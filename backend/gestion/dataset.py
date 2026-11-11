"""
Arma la respuesta de GET /api/dataset con la forma de RawDataset (frontend/lib/types.ts).

De dónde sale cada rubro de costo (como en la PLANILLA COSTO MAYO):
  - Combustible        → litros de cada recorrido × costo por litro del mes (compras de gasoil: neto ÷ litros)
  - Choferes (fijo)    → recibo: total − parte por km
  - Choferes (por km)  → recibo: par_kmre × km recorridos + par_kman × km ancho
                         Los dos se reparten entre los camiones que manejó en el mes según sus km (Costos por dominio!BM:CF)
  - Administración     → recibos de los legajos que no son choferes (estructura)
  - Cubiertas          → km del viaje × "Costo cubiertas" de su tipo de servicio (Costos Totales!B10, Costos variables!D24:D27)
  - Service            → services cargados (Mantenimiento!H, Costos Totales!B9); en un mes sin services cargados,
                         km reales × (precio del service ÷ km) del modelo
  - Amortización       → valor U$S × dólar ÷ meses, de camiones y acoplados activos
  - Seguros            → gastos cargados + seguro de carga (par_scar ÷ 12 por camión activo)
  - Impuestos          → % sobre el neto facturado del mes (estructura)
  - Mantenimiento, Patente y rentas, Gastos generales → tabla Gastos
  Lo que es de un acoplado se le carga al camión que lo lleva. Lo que no tiene dominio es estructura:
  el frontend lo reparte entre los camiones según los km.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal

from . import formulas as fx
from .models import (
    Camiones, Choferes, Clientes, Cobranzas, Gastos, Parametros, Recorridos, RubroCosto, Sueldos, TipoCubierta, Viajes,
)


def armar_dataset(corte=None, fuente='backend'):
    # =====================================================
    # LECTURA
    # =====================================================
    viajes = list(
        Viajes.objects.filter(via_anul=False).select_related(
            'cam_codi__mod_codi', 'cam_codi__cam_acop', 'cho_codi', 'cli_codi', 'gen_codi', 'tse_codi',
            'loc_orig', 'loc_dest', 'fac_codi', 'rec_codi',
        ).order_by('via_fech', 'via_codi')
    )
    gastos = list(Gastos.objects.select_related('rco_codi', 'cam_codi').order_by('gas_fech', 'gas_codi'))
    unidades = list(Camiones.objects.select_related('cho_codi', 'tse_codi', 'mod_codi', 'cam_acop').order_by('cam_pate'))
    camiones = [u for u in unidades if u.cam_tipo == 'C']

    if corte is None:
        fechas = [v.via_fech for v in viajes] + [g.gas_fech for g in gastos]
        corte = max(fechas) if fechas else date.today()
    viajes = [v for v in viajes if v.via_fech <= corte]
    gastos = [g for g in gastos if g.gas_fech <= corte]
    recorridos = [r for r in Recorridos.objects.select_related('cam_codi') if r.rec_fefi <= corte]
    sueldos = list(Sueldos.objects.filter(sue_mes__lte=corte).select_related('per_codi'))
    km_reales = fx.km_reales_por_viaje(viajes)

    parametros = list(Parametros.objects.order_by('par_desd'))
    por_defecto = Parametros()  # valores por defecto del modelo (los del Excel)
    variable = {r.rco_nomb: r.rco_vari for r in RubroCosto.objects.all()}
    costo_cubierta = {t.tcu_codi: fx.costo_por_km(t.tcu_prec, t.tcu_kdur) for t in TipoCubierta.objects.all()}
    meses_con_service = set()  # meses con services cargados: no se calcula service por km

    def par(mes):
        return fx.parametros_vigentes(mes, parametros, por_defecto)

    primera = min([v.via_fech for v in viajes] + [corte])
    meses = list(fx.meses_entre(primera, corte))

    # Lo de un acoplado va al camión que lo lleva (Costos por dominio!AO27:AW46)
    camion_de_acoplado = {}
    for u in camiones:
        if u.cam_acop_id and u.cam_acop_id not in camion_de_acoplado:
            camion_de_acoplado[u.cam_acop_id] = u

    def a_camion(u):
        if u is None or u.cam_tipo == 'C':
            return u
        return camion_de_acoplado.get(u.cam_codi)  # sin camión que lo lleve: estructura

    # Chofer → su camión, y legajo → chofer
    camion_de_chofer = {}
    for d in camiones:
        if d.cho_codi_id and d.cho_codi_id not in camion_de_chofer:
            camion_de_chofer[d.cho_codi_id] = d
    chofer_de_legajo = {c.per_codi_id: c for c in Choferes.objects.filter(per_codi__isnull=False)}

    out_mes, out_dia = [], []

    # =====================================================
    # GASTOS CARGADOS
    # =====================================================
    gasoil = defaultdict(lambda: [Decimal(0), Decimal(0), Decimal(0)])  # mes → [neto, con impuestos, litros]
    for g in gastos:
        rubro = g.rco_codi
        if rubro.rco_nomb == fx.COMBUSTIBLE:
            m = gasoil[fx.primero_de_mes(g.gas_fech)]
            m[0] += g.gas_neto
            m[1] += g.gas_itot
            m[2] += g.gas_litr
            continue
        if rubro.rco_nomb in fx.CALCULADOS:
            continue
        if rubro.rco_nomb == fx.SERVICE:
            meses_con_service.add(fx.primero_de_mes(g.gas_fech))
        dom = a_camion(g.cam_codi)
        if rubro.rco_mens:
            n = max(1, g.gas_cmes or 1)
            for i in range(n):  # seguro trimestral: 1/3 en cada mes (Costos variables!F50 = G50 ÷ 3)
                out_mes.append(_gasto_mes(fx.sumar_meses(fx.primero_de_mes(g.gas_fech), i), rubro.rco_nomb, dom,
                                          g.gas_conc, g.gas_neto / n, rubro.rco_vari))
        else:
            out_dia.append({
                'fecha': _iso(g.gas_fech), 'rubro': rubro.rco_nomb, 'unidad': dom.cam_pate if dom else None,
                'concepto': g.gas_conc, 'monto': float(g.gas_neto),
            })

    precio = {m: fx.precio_gasoil(*gasoil[m]) for m in meses}  # mes → (lista, final)

    # =====================================================
    # COMBUSTIBLE: litros de cada recorrido × costo final del litro en ese mes (Costos por dominio!K × J)
    # =====================================================
    for r in recorridos:
        if r.rec_suml:
            final = precio.get(fx.primero_de_mes(r.rec_fefi), (0, 0))[1]
            dom = a_camion(r.cam_codi)
            out_dia.append({
                'fecha': _iso(r.rec_fefi), 'rubro': fx.COMBUSTIBLE, 'unidad': dom.cam_pate if dom else None,
                'concepto': f'Recorrido {r.rec_codi}', 'monto': float(r.rec_suml * final), 'litros': float(r.rec_suml),
            })

    # =====================================================
    # VIAJES
    # =====================================================
    cobros = defaultdict(list)
    for c in Cobranzas.objects.filter(cob_fech__lte=corte):
        cobros[c.fac_codi_id].append((c.cob_fech, c.cob_itot))
    total_factura = defaultdict(Decimal)
    for v in viajes:
        if v.fac_codi_id:
            total_factura[v.fac_codi_id] += v.via_itot

    out_viajes = []
    for v in viajes:
        dom = v.cam_codi
        km_real = km_reales[v.via_codi]
        # Costos Totales!B10: km del viaje × costo de cubiertas del servicio. El frontend lo multiplica por km reales.
        cub_viaje = fx.cubiertas_servicio_por_km(v.tse_codi, costo_cubierta) * v.via_kcar
        service_km = Decimal(0) if fx.primero_de_mes(v.via_fech) in meses_con_service else fx.service_por_km(dom.mod_codi)
        fac = v.fac_codi
        if fac:
            emision, vence, numero = fac.fac_emis, fac.fac_venc, fac.fac_nume
            cobro = fx.fecha_de_cobro(total_factura[fac.fac_codi], cobros[fac.fac_codi])
        else:  # todavía sin facturar: se debe desde el día del viaje
            emision = vence = v.via_fech
            numero, cobro = '', None
        out_viajes.append({
            'id': v.via_codi,
            'fecha': _iso(v.via_fech),
            'unidad': dom.cam_pate,
            'chofer': v.cho_codi.cho_nomb,
            'cliente': v.cli_codi.cli_nomb,
            'empresa': v.gen_codi.gen_nomb,
            'servicio': v.tse_codi.tse_nomb,
            'origen': v.loc_orig.loc_nomb,
            'destino': v.loc_dest.loc_nomb,
            'kmCargado': float(v.via_kcar),
            'kmReal': float(km_real),
            'flete': float(v.via_flet),
            'descuento': float(v.via_desc),
            'total': float(v.via_itot),
            'costoCubKm': float(cub_viaje / km_real) if km_real else 0.0,
            'costoServiceKm': float(service_km),
            'factura': numero,
            'emision': _iso(emision),
            'vence': _iso(vence),
            'cobro': _iso(cobro),
        })

    # =====================================================
    # RUBROS CALCULADOS POR MES
    # =====================================================
    neto_mes = defaultdict(Decimal)
    for v in viajes:
        neto_mes[fx.primero_de_mes(v.via_fech)] += fx.neto_viaje(v.via_flet, v.via_desc)
    sueldos_mes = defaultdict(list)
    for s in sueldos:
        sueldos_mes[fx.primero_de_mes(s.sue_mes)].append(s)
    # km de cada chofer en cada camión por mes, para repartir su sueldo (Costos por dominio!AP4:BJ18)
    km_chofer = defaultdict(lambda: defaultdict(Decimal))
    camion_por_pk = {d.cam_codi: d for d in camiones}
    for v in viajes:
        km_chofer[(v.cho_codi_id, fx.primero_de_mes(v.via_fech))][v.cam_codi_id] += v.via_kcar

    for mes in meses:
        p = par(mes)
        fin = fx.fin_de_mes(mes)

        # Impuestos: % sobre el neto facturado del mes (Costos varios!B24:B26)
        for concepto, monto in fx.impuestos_del_mes(neto_mes[mes], p):
            out_mes.append(_gasto_mes(mes, fx.IMPUESTOS, None, concepto, monto, variable.get(fx.IMPUESTOS, True)))

        # Sueldos (hoja Sueldos): chofer → fijo y por km en su camión; el resto → Administración
        for s in sueldos_mes[mes]:
            cho = chofer_de_legajo.get(s.per_codi_id)
            if cho:
                var = fx.sueldo_variable(s, p)
                partes = fx.repartir_por_km(1, km_chofer[(cho.cho_codi, mes)])
                if not partes:  # sin viajes en el mes: a su camión asignado (o a estructura si no tiene)
                    asignado = camion_de_chofer.get(cho.cho_codi)
                    partes = {asignado.cam_codi if asignado else None: Decimal(1)}
                for pk, f in partes.items():
                    dom = camion_por_pk.get(pk)
                    out_mes.append(_gasto_mes(mes, fx.CHOFERES_FIJO, dom, cho.cho_nomb, (s.sue_itot - var) * f, False))
                    out_mes.append(_gasto_mes(mes, fx.CHOFERES_KM, dom, cho.cho_nomb, var * f, variable.get(fx.CHOFERES_KM, True)))
            else:
                out_mes.append(_gasto_mes(mes, fx.ADMINISTRACION, None, s.per_codi.per_nomb, s.sue_itot, False))

        # Amortización: U$S × dólar ÷ meses, de camiones y acoplados activos (Costos variables!C37:I38)
        for d in unidades:
            monto = fx.amortizacion_mensual(fx.valor_en_pesos(d, p.par_dola), d.cam_vuti)
            if monto and _activo(d.cam_alta, d.cam_baja, mes, fin):
                out_mes.append(_gasto_mes(mes, fx.AMORTIZACION, a_camion(d), f'{d.cam_pate} a {d.cam_vuti} meses', monto, False))

        # Seguro de carga: póliza anual por camión ÷ 12 (Costos por dominio!P)
        if p.par_scar:
            for d in camiones:
                if _activo(d.cam_alta, d.cam_baja, mes, fin):
                    out_mes.append(_gasto_mes(mes, 'Seguros', d, 'Seguro de carga', p.par_scar / 12, False))

    return {
        'fechaCorte': _iso(corte),
        'fuente': fuente,
        'unidades': [
            {
                'id': d.cam_pate,
                'modelo': d.mod_codi.mod_nomb if d.mod_codi else '',
                'servicio': d.tse_codi.tse_nomb if d.tse_codi else '',
                'chofer': d.cho_codi.cho_nomb if d.cho_codi else '',
            }
            for d in camiones
        ],
        'clientes': [{'nombre': c.cli_nomb} for c in Clientes.objects.order_by('cli_nomb')],
        'viajes': out_viajes,
        'gastosMes': out_mes,
        'gastosDia': out_dia,
        'gasoil': [{'mes': f'{m:%Y-%m}', 'lista': float(precio[m][0]), 'final': float(precio[m][1])} for m in meses],
    }


#--------------------------------------------------------AUXILIARES↓-----------------------------------------------------------------

def _gasto_mes(mes, rubro, dominio, concepto, monto, es_variable):
    return {
        'mes': f'{mes:%Y-%m}',
        'rubro': rubro,
        'unidad': dominio.cam_pate if dominio else None,
        'concepto': concepto,
        'monto': float(monto or 0),
        'variable': bool(es_variable),
    }


def _activo(alta, baja, desde, hasta):
    return (alta is None or alta <= hasta) and (baja is None or baja >= desde)


def _iso(d):
    return d.isoformat() if d else None
