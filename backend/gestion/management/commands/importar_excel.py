"""
python manage.py importar_excel ["../datos/PLANILLA COSTO MAYO.xlsx"]

Borra los datos y carga la PLANILLA COSTO MAYO tal cual, hoja por hoja:

  Detalles viajes mayo  → General, Localidad, Clientes, TipoServicio, Choferes, Viajes
  Costos por dominio    → Camiones (C5:G24 camiones, C27:G57 acoplados) y qué acoplado lleva cada uno (AO27:AQ46)
  Sueldos x km          → chofer asignado a cada camión
  Costos variables      → Parametros (C16, H11:H14), TipoCubierta (C19:F21), cubiertas por servicio (L24:P27),
                          Modelo (C30:E34), Seguros / Patente y rentas por dominio (C50:F102)
  Costos varios         → Gastos generales (A5:B23) y % de impuestos (E9:E11)
  Sueldos               → LegajoPersonal y Sueldos (A3:F24 y el desagregado I3:S18)
  Combustible           → Recorridos (km reales y litros por camión) + la compra de gasoil del mes
  Mantenimiento         → Mantenimiento (E) y Service (H) por dominio
"""
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestion import formulas as fx
from gestion.models import (
    General, Parametros, Provincia, Localidad, LegajoPersonal, Choferes, Sueldos, Clientes, TipoServicio, TipoCubierta,
    Modelo, Camiones, Recorridos, Facturas, Viajes, Cobranzas, RubroCosto, Gastos,
)

ARCHIVO = Path(settings.BASE_DIR).parent / 'datos' / 'PLANILLA COSTO MAYO.xlsx'
# De hijas a madres, para poder borrar sin romper las relaciones
BORRAR = [Gastos, Cobranzas, Viajes, Recorridos, Facturas, Sueldos, Camiones, Modelo, Clientes, Choferes, LegajoPersonal,
          Localidad, Provincia, TipoServicio, TipoCubierta, General, Parametros, RubroCosto]
# Mantenimiento!G agrupa los camiones por equipo; sirve para los que no tienen viajes en el mes
EQUIPO = {'BATEA': 'BATEA CEREAL', 'CARRETON': 'CARRETON', 'CAMILLAS': 'CAMILLA', 'BITRENES': 'BITREN'}
CODIGO_SIN_VIAJES = 9000  # código para camiones y acoplados que no aparecen en Detalles viajes


def num(x):
    """Número de una celda: acepta texto con coma decimal ('35,07')."""
    if x is None or x == '' or x == '-':
        return Decimal(0)
    if isinstance(x, str):
        x = x.strip().replace('.', '').replace(',', '.') if ',' in x else x.strip()
        return Decimal(x) if x else Decimal(0)
    return Decimal(str(x))


def dos(x):
    return Decimal(x).quantize(Decimal('0.01'))


def pat(x):
    """Patente normalizada: 'NUB242' y 'NUB 242' son la misma."""
    return re.sub(r'\s+', '', str(x or '')).upper()


def nombre(x):
    return re.sub(r'\s+', ' ', str(x or '')).strip().upper()


def fecha(x):
    return x.date() if isinstance(x, datetime) else x


class Command(BaseCommand):
    help = 'Borra los datos y carga la PLANILLA COSTO MAYO tal cual.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', nargs='?', default=str(ARCHIVO))

    @transaction.atomic
    def handle(self, archivo, **options):
        if not Path(archivo).exists():
            raise CommandError(f'No existe {archivo}')
        wb = openpyxl.load_workbook(archivo, data_only=True)
        Camiones.objects.update(cam_acop=None)  # un camión apunta a su acoplado: soltarlo para poder borrar
        for model in BORRAR:
            model.objects.all().delete()

        cv, cvar, su, sxk, co, mt, cd = (wb['Costos variables'], wb['Costos varios'], wb['Sueldos'], wb['Sueldos x km'],
                                         wb['Combustible'], wb['Mantenimiento'], wb['Costos por dominio'])
        dv = wb['Detalles viajes mayo']
        enc = [c.value for c in dv[1]]
        filas = [dict(zip(enc, [c.value for c in r])) for r in dv.iter_rows(min_row=2) if r[0].value]
        mes = date(fecha(filas[0]['Fecha']).year, fecha(filas[0]['Fecha']).month, 1)
        fin_mes = fx.fin_de_mes(mes)

        # =====================================================
        # RUBROS Y PARÁMETROS
        # =====================================================
        rubros = {}
        for codi, nomb, vari, mens in fx.RUBROS_BASE:
            rubros[nomb] = RubroCosto.objects.create(rco_codi=codi, rco_nomb=nomb, rco_vari=vari, rco_mens=mens)

        Parametros.objects.create(
            par_codi=1, par_desd=date(2000, 1, 1),
            par_iibb=num(cvar['E9'].value) * 100, par_muni=num(cvar['E10'].value) * 100, par_gana=num(cvar['E11'].value) * 100,
            par_kmre=num(su['O4'].value), par_kman=num(su['P4'].value),
            # Costos por dominio!P tiene un seguro de carga de 336.842 al año, pero Costos Totales!B4 no lo suma
            par_scar=0,
            par_dola=num(cv['C16'].value),
        )

        # =====================================================
        # CUBIERTAS, SERVICE Y TIPOS DE SERVICIO
        # =====================================================
        tipo_cub = {}
        for i, r in enumerate(range(19, 22), start=1):
            tipo_cub[cv[f'C{r}'].value] = TipoCubierta.objects.create(
                tcu_codi=i, tcu_nomb=cv[f'C{r}'].value, tcu_prec=num(cv[f'E{r}'].value), tcu_kdur=num(cv[f'F{r}'].value))

        # L24:P27 → cantidad de cada tipo de cubierta por equipo (CARRETON toma 3 ejes, como D24)
        cub_servicio = {}
        for r in range(24, 28):
            cant = {'LINEAL': 0, 'TACO': 0, 'CARRETON': 0}
            cant[cv[f'M{r}'].value] += int(num(cv[f'N{r}'].value))
            if r == 25:  # CAMILLA: LINEAL + TACO
                cant[cv[f'O{r}'].value] += int(num(cv[f'P{r}'].value))
            equipo = {'CARRETON': 'CARRETON', 'CAMILLA': 'CAMILLA', 'BITREN': 'BITREN', 'BATEA': 'BATEA CEREAL'}[cv[f'C{r}'].value]
            cub_servicio[equipo] = cant

        # Tipo Carga Cod → nombre más usado (hay un viaje con 'ca' en vez de CAMILLA)
        por_codigo = defaultdict(Counter)
        for f in filas:
            por_codigo[int(f['Tipo Carga Cod'])][nombre(f['Tipo Carga Desc'])] += 1
        servicios = {}
        for codi, nombres in sorted(por_codigo.items()):
            nomb = nombres.most_common(1)[0][0]
            c = cub_servicio.get(nomb, {})
            servicios[codi] = TipoServicio.objects.create(
                tse_codi=codi, tse_nomb=nomb,
                tse_clin=c.get('LINEAL', 0), tse_ctac=c.get('TACO', 0), tse_ccar=c.get('CARRETON', 0))
        servicio_por_nombre = {s.tse_nomb: s for s in servicios.values()}

        modelos = {}
        for i, r in enumerate(range(30, 35), start=1):
            modelos[cv[f'C{r}'].value] = Modelo.objects.create(
                mod_codi=i, mod_nomb=cv[f'C{r}'].value, mod_kdur=num(cv[f'D{r}'].value), mod_isvc=num(cv[f'E{r}'].value))

        # =====================================================
        # EMPRESAS, LOCALIDADES, CLIENTES
        # =====================================================
        empresas, localidades, clientes = {}, {}, {}
        for f in filas:
            codi, nomb = f['Empresa'].split(' - ', 1)
            empresas.setdefault(f['Empresa'], (int(codi), nomb.strip()))
            localidades.setdefault(int(f['Cod.Origen']), f['Origen'].strip())
            localidades.setdefault(int(f['Cod.Destino']), f['Destino'].strip())
            clientes.setdefault(int(f['Cod.Clie']), f['Cliente'].strip())
        empresas = {k: General.objects.create(gen_codi=c, gen_nomb=n) for k, (c, n) in empresas.items()}
        localidades = {c: Localidad.objects.create(loc_codi=c, loc_nomb=n) for c, n in localidades.items()}
        clientes = {c: Clientes.objects.create(cli_codi=c, cli_nomb=n) for c, n in clientes.items()}

        # =====================================================
        # PERSONAL: Sueldos!A3:F24 (puesto y monto) + I3:S18 (km del recibo de cada chofer)
        # =====================================================
        km_recibo = {}
        for r in range(4, 19):
            if su[f'J{r}'].value:
                km_recibo[nombre(su[f'J{r}'].value)] = (num(su[f'R{r}'].value), num(su[f'S{r}'].value))

        legajos = {}  # nombre → (legajo, es chofer)
        sig_admin = 1000
        for r in range(3, 25):
            puesto, monto = su[f'A{r}'].value, su[f'F{r}'].value
            if not puesto or monto is None:
                continue
            es_chofer = puesto.strip().lower() == 'chofer'
            if es_chofer:
                nomb = nombre(su[f'C{r}'].value)
            else:  # los administrativos solo figuran como "HABERES (VARELA)"
                m = re.search(r'\((.*?)\)', su[f'D{r}'].value or '')
                nomb = nombre(m.group(1) if m else su[f'D{r}'].value)
            legajos[nomb] = (num(monto), es_chofer)

        choferes_viajes = {}
        for f in filas:
            choferes_viajes.setdefault(nombre(f['Chofer']), int(f['Cod.Chofer']))

        choferes, nuevos_sueldos = {}, []
        for nomb, codi in sorted(choferes_viajes.items(), key=lambda x: x[1]):
            per = None
            if nomb in legajos and legajos[nomb][1]:  # solo se une al recibo si en Sueldos figura como chofer
                per = LegajoPersonal.objects.create(per_codi=codi, per_nomb=nomb)
            choferes[nomb] = Choferes.objects.create(cho_codi=codi, cho_nomb=nomb, per_codi=per)
        sig_chofer = max(choferes_viajes.values()) + 1
        for nomb, (monto, es_chofer) in legajos.items():
            per = LegajoPersonal.objects.filter(per_nomb=nomb).first()
            if per is None:
                if es_chofer:  # chofer sin viajes en el mes (ej. licencia)
                    per = LegajoPersonal.objects.create(per_codi=sig_chofer, per_nomb=nomb)
                    choferes[nomb] = Choferes.objects.create(cho_codi=sig_chofer, cho_nomb=nomb, per_codi=per)
                    sig_chofer += 1
                else:
                    per = LegajoPersonal.objects.create(per_codi=sig_admin, per_nomb=nomb)
                    sig_admin += 1
            kmre, kman = km_recibo.get(nomb, (0, 0)) if es_chofer else (0, 0)
            nuevos_sueldos.append(Sueldos(sue_codi=len(nuevos_sueldos) + 1, sue_mes=mes, sue_itot=monto,
                                          sue_kmre=kmre, sue_kman=kman, per_codi=per))
        Sueldos.objects.bulk_create(nuevos_sueldos)

        # =====================================================
        # CAMIONES Y ACOPLADOS
        # =====================================================
        cod_camion, cod_acop, serv_camion = {}, {}, defaultdict(Counter)
        for f in filas:
            cod_camion[pat(f['Dominio Camion'])] = int(f['Cod.Camion'])
            serv_camion[pat(f['Dominio Camion'])][int(f['Tipo Carga Cod'])] += 1
            if f['Dominio Acop']:
                cod_acop[pat(f['Dominio Acop'])] = int(f['Cod.Acop'])
        equipo_mant, actual = {}, None
        for r in range(6, 26):
            actual = EQUIPO.get(nombre(mt[f'G{r}'].value), actual)
            equipo_mant[pat(mt[f'A{r}'].value)] = actual

        chofer_asignado = {}
        for r in range(3, 23):
            n = nombre(sxk[f'C{r}'].value)
            if n in choferes:
                chofer_asignado[pat(sxk[f'B{r}'].value)] = choferes[n]

        sig = CODIGO_SIN_VIAJES
        dominios = {}

        def codigo(p, tabla):
            nonlocal sig
            if p in tabla and tabla[p] not in {d.cam_codi for d in dominios.values()}:
                return tabla[p]
            sig += 1
            return sig

        for r in range(5, 58):
            p = pat(cd[f'C{r}'].value)
            if not p or cd[f'H{r}'].value is None or (r > 24 and cd[f'E{r}'].value is None):
                continue  # títulos de grupo (ENGANCHES, CARRETONES, BATEAS…)
            es_camion = r <= 24
            if es_camion:
                tse = servicios[serv_camion[p].most_common(1)[0][0]] if serv_camion[p] else servicio_por_nombre.get(equipo_mant.get(p))
            dominios[p] = Camiones.objects.create(
                cam_codi=codigo(p, cod_camion if es_camion else cod_acop), cam_pate=cd[f'C{r}'].value.strip(),
                cam_tipo='C' if es_camion else 'A',
                cam_clin=int(num(cd[f'E{r}'].value)), cam_ctac=int(num(cd[f'F{r}'].value)), cam_ccar=int(num(cd[f'G{r}'].value)),
                # Amortización: Costos Totales!B11 apunta a una celda vacía; no se carga valor del camión
                cam_vusd=0,
                mod_codi=modelos.get(cd[f'D{r}'].value) if es_camion else None,
                tse_codi=tse if es_camion else None,
                cho_codi=chofer_asignado.get(p) if es_camion else None,
            )
        # Acoplados que figuran en Costos variables (patente, seguro) o Mantenimiento pero no en Costos por dominio
        for p_txt in [cv[f'C{r}'].value for r in range(50, 103)] + [mt[f'A{r}'].value for r in range(27, 58)]:
            p = pat(p_txt)
            if p and p not in dominios and p not in {'CAMIONES', 'ENGANCHES', 'CARRETONES', 'BATEAS', 'TOLVAS', 'SEMIS'}:
                dominios[p] = Camiones.objects.create(cam_codi=codigo(p, cod_acop), cam_pate=p_txt.strip(), cam_tipo='A')
        # Qué acoplado lleva cada camión (Costos por dominio!AO27:AP46)
        for r in range(27, 47):
            cam, acop = pat(cd[f'AO{r}'].value), pat(cd[f'AP{r}'].value)
            if cam in dominios and acop in dominios:
                Camiones.objects.filter(pk=dominios[cam].pk).update(cam_acop=dominios[acop])

        # =====================================================
        # RECORRIDOS (hoja Combustible): un recorrido por camión en el mes
        # =====================================================
        recorridos = {}
        for r in range(4, 21):
            p = pat(co[f'B{r}'].value)
            if p in dominios:
                recorridos[p] = Recorridos.objects.create(
                    rec_codi=r - 3, rec_fein=mes, rec_fefi=fin_mes, cam_codi=dominios[p],
                    rec_tkms=num(co[f'F{r}'].value), rec_suml=num(co[f'G{r}'].value))

        # =====================================================
        # VIAJES (Detalles viajes mayo)
        # =====================================================
        nuevos = []
        for f in filas:
            p = pat(f['Dominio Camion'])
            nuevos.append(Viajes(
                via_codi=int(f['Cod.Venta']), via_fech=fecha(f['Fecha']), via_kcar=num(f['Kms']),
                via_flet=num(f['Flete']), via_desc=num(f['Descuento']), via_itot=num(f['Total']),
                via_anul=False,
                cam_codi=dominios[p], cho_codi=choferes[nombre(f['Chofer'])], cli_codi=clientes[int(f['Cod.Clie'])],
                gen_codi=empresas[f['Empresa']], tse_codi=servicios[int(f['Tipo Carga Cod'])],
                loc_orig=localidades[int(f['Cod.Origen'])], loc_dest=localidades[int(f['Cod.Destino'])],
                rec_codi=recorridos.get(p),
            ))
        Viajes.objects.bulk_create(nuevos)

        # =====================================================
        # GASTOS
        # =====================================================
        gastos = []

        def gasto(fech, rubro, conc, neto, dom=None, **extra):
            gastos.append(Gastos(gas_codi=len(gastos) + 1, gas_fech=fech, gas_conc=conc, gas_neto=dos(neto),
                                 rco_codi=rubros[rubro], cam_codi=dom, **extra))

        # Combustible: litros × costo final del litro (Costos Totales!B8 = C12 × C14)
        litros, final, lista = num(cv['C12'].value), num(cv['C14'].value), num(cv['H11'].value)
        gasto(fin_mes, fx.COMBUSTIBLE, 'Gasoil del mes (Costos variables)', litros * final,
              gas_litr=litros, gas_itot=dos(litros * lista))

        # Mantenimiento!E (correctivos) y H (service), por dominio
        for r in range(6, 58):
            p = pat(mt[f'A{r}'].value)
            if p not in dominios:
                continue
            if num(mt[f'E{r}'].value):
                gasto(fin_mes, 'Mantenimiento', 'Mantenimiento del mes', num(mt[f'E{r}'].value), dominios[p])
            if r <= 25 and num(mt[f'H{r}'].value):
                gasto(fin_mes, fx.SERVICE, 'Service', num(mt[f'H{r}'].value), dominios[p])

        # Costos variables!C50:F102: patente, rentas y seguro mensual por dominio
        for r in range(50, 103):
            p = pat(cv[f'C{r}'].value)
            if p not in dominios:
                continue
            for col, rubro, conc in (('D', 'Patente y rentas', 'Patente'), ('E', 'Patente y rentas', 'Rentas'),
                                     ('F', 'Seguros', 'Seguro mensual')):
                if num(cv[f'{col}{r}'].value):
                    gasto(mes, rubro, conc, num(cv[f'{col}{r}'].value), dominios[p])

        # Costos varios!A5:B23 (B24:B26 son los impuestos: los calcula el backend con E9:E11)
        for r in range(5, 24):
            if num(cvar[f'B{r}'].value):
                gasto(mes, 'Gastos generales', cvar[f'A{r}'].value.strip(), num(cvar[f'B{r}'].value))

        Gastos.objects.bulk_create(gastos)

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {len(nuevos)} viajes, {len(clientes)} clientes, {Camiones.objects.filter(cam_tipo="C").count()} camiones, '
            f'{Camiones.objects.filter(cam_tipo="A").count()} acoplados, {len(choferes)} choferes, '
            f'{len(nuevos_sueldos)} recibos, {len(recorridos)} recorridos, {len(gastos)} gastos.'
        ))
