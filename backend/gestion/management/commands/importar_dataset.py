"""
python manage.py importar_dataset archivo.json [--borrar]

Carga un JSON con la forma de RawDataset (la misma que devuelve GET /api/dataset) en las tablas.
Sirve para pasar los datos de prueba del frontend al backend.

Cómo se convierte cada cosa:
  - unidades / viajes   → Camiones, Choferes (+ su legajo), Clientes, Localidad, TipoServicio, Modelo, General
  - km reales y litros  → Recorridos (uno por camión y mes)
  - factura / cobro     → Facturas y Cobranzas
  - Choferes (fijo + por km) y sueldos de administración → Sueldos (un recibo por empleado y mes)
  - Amortización        → cam_vusd del camión
  - $/km de cubiertas y service → cantidades de cubiertas del camión y precio del service del modelo (aproximado)
  - Combustible         → un gasto de gasoil por mes (neto, con impuestos y litros) para el precio por litro
  - Mantenimiento, Seguros, Patente y rentas, Gastos generales, otros de Administración → Gastos
  - Impuestos, Cubiertas, Service → no se cargan: los calcula GET /api/dataset
"""
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestion import formulas as fx
from gestion.models import (
    General, Localidad, LegajoPersonal, Choferes, Sueldos, Clientes, TipoServicio, TipoCubierta, Modelo, Camiones,
    Recorridos, Facturas, Viajes, Cobranzas, RubroCosto, Gastos, Parametros,
)

# De hijas a madres, para poder borrar sin romper las relaciones
BORRAR = [Gastos, Cobranzas, Viajes, Recorridos, Facturas, Sueldos, Camiones, Modelo, Clientes, Choferes,
          LegajoPersonal, Localidad, General]
KM_SERVICE = Decimal(30000)  # Costos variables!D30: cada cuántos km se hace el service


def d(s):
    return date.fromisoformat(s) if s else None


def dec(x):
    return Decimal(str(round(x, 2))) if x is not None else None


class Command(BaseCommand):
    help = 'Carga un JSON con la forma de RawDataset (frontend/lib/types.ts) en las tablas.'

    def add_arguments(self, parser):
        parser.add_argument('archivo')
        parser.add_argument('--borrar', action='store_true', help='Borra viajes, gastos, dominios, clientes, etc. antes de cargar')

    @transaction.atomic
    def handle(self, archivo, borrar, **options):
        with open(archivo, encoding='utf-8') as f:
            raw = json.load(f)

        rubros = {r.rco_nomb: r for r in RubroCosto.objects.all()}
        faltan = {g['rubro'] for g in raw['gastosMes'] + raw['gastosDia']} - set(rubros)
        if faltan:
            raise CommandError(f'Faltan rubros {sorted(faltan)}. Correr antes: python manage.py cargar_base')
        par = Parametros.objects.order_by('-par_desd').first() or Parametros()

        if borrar:
            for model in BORRAR:
                model.objects.all().delete()

        viajes = raw['viajes']

        # =====================================================
        # TABLAS DE NOMBRES (se crean con códigos correlativos)
        # =====================================================
        def codigos(model, pk, campo, nombres, extra=None):
            existentes = {getattr(o, campo): o for o in model.objects.all()}
            sig = max([getattr(o, pk) for o in existentes.values()] + [0]) + 1
            for n in sorted(set(nombres) - set(existentes)):
                existentes[n] = model.objects.create(**{pk: sig, campo: n, **((extra or {}).get(n, {}))})
                sig += 1
            return existentes

        empresas = codigos(General, 'gen_codi', 'gen_nomb', [v['empresa'] for v in viajes])
        localidades = codigos(Localidad, 'loc_codi', 'loc_nomb', [v['origen'] for v in viajes] + [v['destino'] for v in viajes])
        servicios = codigos(TipoServicio, 'tse_codi', 'tse_nomb', [u['servicio'] for u in raw['unidades']] + [v['servicio'] for v in viajes])
        clientes = codigos(Clientes, 'cli_codi', 'cli_nomb', [c['nombre'] for c in raw['clientes']] + [v['cliente'] for v in viajes])

        # Modelo: precio del service tal que precio ÷ km = el $/km de service del dato de prueba
        svc = defaultdict(list)
        modelo_de = {u['id']: u['modelo'] for u in raw['unidades']}
        for v in viajes:
            if v['unidad'] in modelo_de:
                svc[modelo_de[v['unidad']]].append(v['costoServiceKm'])
        modelos = codigos(Modelo, 'mod_codi', 'mod_nomb', [u['modelo'] for u in raw['unidades']], {
            m: {'mod_kdur': KM_SERVICE, 'mod_isvc': dec(sum(x) / len(x) * float(KM_SERVICE)) if x else Decimal(0)}
            for m, x in svc.items()
        } | {m: {'mod_kdur': KM_SERVICE, 'mod_isvc': Decimal(0)} for m in modelo_de.values() if m not in svc})

        # Choferes, cada uno con su legajo (mismo código)
        nombres_chofer = sorted({u['chofer'] for u in raw['unidades'] if u['chofer']} | {v['chofer'] for v in viajes if v['chofer']})
        choferes = {o.cho_nomb: o for o in Choferes.objects.all()}
        sig = max([o.cho_codi for o in choferes.values()] + list(LegajoPersonal.objects.values_list('per_codi', flat=True)) + [0]) + 1
        for n in nombres_chofer:
            if n not in choferes:
                per = LegajoPersonal.objects.create(per_codi=sig, per_nomb=n)
                choferes[n] = Choferes.objects.create(cho_codi=sig, cho_nomb=n, per_codi=per)
                sig += 1

        # =====================================================
        # CAMIONES: cubiertas LINEAL tal que cantidad × $/km ≈ el $/km de cubiertas del dato de prueba
        # =====================================================
        cub = defaultdict(list)
        for v in viajes:
            cub[v['unidad']].append(v['costoCubKm'])
        lineal = TipoCubierta.objects.filter(tcu_codi=1).first()
        cxkm_lineal = float(fx.costo_por_km(lineal.tcu_prec, lineal.tcu_kdur)) if lineal else 0
        dominios = {o.cam_pate: o for o in Camiones.objects.all()}
        sig = max([o.cam_codi for o in dominios.values()] + [0]) + 1
        for u in raw['unidades']:
            if u['id'] not in dominios:
                x = cub.get(u['id'])
                dominios[u['id']] = Camiones.objects.create(
                    cam_codi=sig, cam_pate=u['id'], mod_codi=modelos[u['modelo']], tse_codi=servicios[u['servicio']],
                    cho_codi=choferes.get(u['chofer']),
                    cam_clin=round(sum(x) / len(x) / cxkm_lineal) if x and cxkm_lineal else 0,
                )
                sig += 1

        # =====================================================
        # RECORRIDOS: uno por camión y por mes, con los km reales y los litros
        # =====================================================
        grupo = defaultdict(lambda: {'km': Decimal(0), 'litros': Decimal(0), 'fechas': []})
        for v in viajes:
            g = grupo[(v['unidad'], v['fecha'][:7])]
            g['km'] += dec(v['kmReal'])
            g['fechas'].append(d(v['fecha']))
        for g in raw['gastosDia']:
            if g['rubro'] == fx.COMBUSTIBLE and g.get('litros') and g['unidad'] and (g['unidad'], g['fecha'][:7]) in grupo:
                grupo[(g['unidad'], g['fecha'][:7])]['litros'] += dec(g['litros'])
        rec_sig = max(Recorridos.objects.values_list('rec_codi', flat=True), default=0) + 1
        recorridos = {}
        for (pate, mes), g in sorted(grupo.items()):
            recorridos[(pate, mes)] = Recorridos(
                rec_codi=rec_sig, rec_fein=min(g['fechas']), rec_fefi=max(g['fechas']),
                rec_tkms=g['km'], rec_suml=g['litros'], cam_codi=dominios[pate],
            )
            rec_sig += 1
        Recorridos.objects.bulk_create(recorridos.values(), batch_size=1000)

        # =====================================================
        # FACTURAS, VIAJES Y COBRANZAS
        # =====================================================
        fac_sig = max(Facturas.objects.values_list('fac_codi', flat=True), default=0) + 1
        via_sig = max(Viajes.objects.values_list('via_codi', flat=True), default=0) + 1
        cob_sig = max(Cobranzas.objects.values_list('cob_codi', flat=True), default=0) + 1
        facturas, nuevos_viajes, cobros = {}, [], []
        total_fac = defaultdict(Decimal)
        for v in viajes:
            total_fac[(v['empresa'], v['factura'])] += dec(v['total'])
        for v in viajes:
            fac = None
            if v['factura']:
                k = (v['empresa'], v['factura'])
                if k not in facturas:
                    facturas[k] = Facturas(
                        fac_codi=fac_sig, fac_nume=v['factura'], fac_emis=d(v['emision']), fac_venc=d(v['vence']),
                        cli_codi=clientes[v['cliente']], gen_codi=empresas[v['empresa']],
                    )
                    fac_sig += 1
                    if v['cobro']:
                        cobros.append(Cobranzas(cob_codi=cob_sig, cob_fech=d(v['cobro']), cob_itot=total_fac[k], fac_codi=facturas[k]))
                        cob_sig += 1
                fac = facturas[k]
            nuevos_viajes.append(Viajes(
                via_codi=via_sig, via_fech=d(v['fecha']), via_kcar=dec(v['kmCargado']),
                via_flet=dec(v['flete']), via_desc=dec(v['descuento']), via_itot=dec(v['total']),
                cam_codi=dominios[v['unidad']], cho_codi=choferes[v['chofer']], cli_codi=clientes[v['cliente']],
                gen_codi=empresas[v['empresa']], tse_codi=servicios[v['servicio']],
                loc_orig=localidades[v['origen']], loc_dest=localidades[v['destino']],
                rec_codi=recorridos[(v['unidad'], v['fecha'][:7])], fac_codi=fac,
            ))
            via_sig += 1
        Facturas.objects.bulk_create(facturas.values(), batch_size=1000)
        Viajes.objects.bulk_create(nuevos_viajes, batch_size=1000)
        Cobranzas.objects.bulk_create(cobros, batch_size=1000)

        # =====================================================
        # SUELDOS: un recibo por empleado y mes. Km del recibo tal que par_kmre × km = la parte por km del dato
        # =====================================================
        recibos = defaultdict(lambda: {'fijo': Decimal(0), 'km': Decimal(0)})
        ultimo = {}
        legajos_admin = {o.per_nomb: o for o in LegajoPersonal.objects.filter(chofer__isnull=True)}
        per_sig = max(LegajoPersonal.objects.values_list('per_codi', flat=True), default=0) + 1
        for g in sorted(raw['gastosMes'], key=lambda g: g['mes']):
            ultimo[(g['rubro'], g['unidad'], g['concepto'])] = g['monto']
            if g['rubro'] in (fx.CHOFERES_FIJO, fx.CHOFERES_KM) and g['concepto'] in choferes:
                r = recibos[(choferes[g['concepto']].per_codi_id, g['mes'])]
                r['fijo' if g['rubro'] == fx.CHOFERES_FIJO else 'km'] += dec(g['monto'])
            elif es_sueldo_admin(g):
                if g['concepto'] not in legajos_admin:
                    legajos_admin[g['concepto']] = LegajoPersonal.objects.create(per_codi=per_sig, per_nomb=g['concepto'])
                    per_sig += 1
                recibos[(legajos_admin[g['concepto']].pk, g['mes'])]['fijo'] += dec(g['monto'])
        sue_sig = max(Sueldos.objects.values_list('sue_codi', flat=True), default=0) + 1
        nuevos_sueldos = []
        for (per_pk, mes), r in sorted(recibos.items()):
            nuevos_sueldos.append(Sueldos(
                sue_codi=sue_sig, sue_mes=d(mes + '-01'), per_codi_id=per_pk, sue_itot=r['fijo'] + r['km'],
                sue_kmre=(r['km'] / par.par_kmre).quantize(Decimal('0.01')) if par.par_kmre else Decimal(0),
            ))
            sue_sig += 1
        Sueldos.objects.bulk_create(nuevos_sueldos, batch_size=1000)

        # Amortización → valor en U$S del camión (cuota del último mes × meses ÷ dólar)
        for (rubro, unidad, concepto), monto in ultimo.items():
            if rubro == fx.AMORTIZACION and unidad in dominios and par.par_dola:
                dom = dominios[unidad]
                Camiones.objects.filter(pk=dom.pk).update(cam_vusd=dec(monto * dom.cam_vuti / float(par.par_dola)))

        # =====================================================
        # GASTOS
        # =====================================================
        gas_sig = max(Gastos.objects.values_list('gas_codi', flat=True), default=0) + 1
        nuevos = []

        # Gasoil: una compra por mes con neto, total con impuestos y litros (para el precio por litro)
        lista = {g['mes']: g['lista'] for g in raw['gasoil']}
        comb = defaultdict(lambda: [0.0, 0.0])
        for g in raw['gastosDia']:
            if g['rubro'] == fx.COMBUSTIBLE:
                c = comb[g['fecha'][:7]]
                c[0] += g['monto']
                c[1] += g.get('litros') or 0
        for mes, (neto, litros) in sorted(comb.items()):
            nuevos.append(Gastos(
                gas_codi=gas_sig, gas_fech=d(mes + '-01'), gas_conc='Gasoil del mes', rco_codi=rubros[fx.COMBUSTIBLE],
                gas_neto=dec(neto), gas_litr=dec(litros), gas_itot=dec(lista.get(mes, 0) * litros),
            ))
            gas_sig += 1

        def es_gasto(g):
            return g['rubro'] not in fx.CALCULADOS and not es_sueldo_admin(g)

        filas = [(d(g['mes'] + '-01'), g) for g in raw['gastosMes'] if es_gasto(g)] + \
                [(d(g['fecha']), g) for g in raw['gastosDia'] if es_gasto(g)]
        for fecha, g in sorted(filas, key=lambda f: f[0]):
            nuevos.append(Gastos(
                gas_codi=gas_sig, gas_fech=fecha, gas_conc=g['concepto'], gas_neto=dec(g['monto']),
                rco_codi=rubros[g['rubro']], cam_codi=dominios.get(g['unidad']),
            ))
            gas_sig += 1
        Gastos.objects.bulk_create(nuevos, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {len(nuevos_viajes)} viajes, {len(facturas)} facturas, {len(cobros)} cobranzas, "
            f"{len(nuevos_sueldos)} recibos, {len(nuevos)} gastos."
        ))


def es_sueldo_admin(g):
    return g['rubro'] == fx.ADMINISTRACION and g['concepto'].lower().startswith('sueldo')
