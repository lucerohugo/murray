"""
Fórmulas de la PLANILLA COSTO MAYO que resuelve el backend.

El resto (costo por km, neto por dominio, reparto de estructura por km, dominios parados, cartera)
lo calcula el frontend en lib/engine.ts con los datos que entrega GET /api/dataset.
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal


#--------------------------------------------------------RUBROS DE COSTO↓-----------------------------------------------------------
# (rco_codi, rco_nomb, rco_vari, rco_mens). Los nombres tienen que ser iguales a los del frontend (lib/engine.ts → RUBROS).
# rco_mens: el gasto se reparte en el mes de su fecha (gas_fech) en vez de caer ese día.

RUBROS_BASE = [
    (1, 'Combustible', True, False),
    (2, 'Choferes (fijo)', False, True),
    (3, 'Choferes (por km)', True, True),
    (4, 'Administración', False, True),
    (5, 'Mantenimiento', False, False),
    (6, 'Cubiertas', True, False),
    (7, 'Service', True, False),
    (8, 'Amortización', False, True),
    (9, 'Seguros', False, True),
    (10, 'Patente y rentas', False, True),
    (11, 'Gastos generales', False, True),
    (12, 'Impuestos', True, True),
]

COMBUSTIBLE, CHOFERES_FIJO, CHOFERES_KM, ADMINISTRACION, AMORTIZACION, IMPUESTOS = (
    'Combustible', 'Choferes (fijo)', 'Choferes (por km)', 'Administración', 'Amortización', 'Impuestos',
)
SERVICE = 'Service'
# Se calculan con fórmulas: si se cargan como gasto, no se suman (Combustible: solo se usa para el precio por litro).
# Service no está: si el mes tiene services cargados (Mantenimiento!H) se usan esos; si no, $/km del modelo × km.
CALCULADOS = {CHOFERES_FIJO, CHOFERES_KM, AMORTIZACION, IMPUESTOS, 'Cubiertas', COMBUSTIBLE}


#--------------------------------------------------------FÓRMULAS↓-------------------------------------------------------------------

def precio_gasoil(neto, total, litros):
    """
    Costos variables!H11 y H14 por mes, pero con las compras reales:
      lista = lo facturado por litro con impuestos   (en el Excel: H11, precio de lista)
      final = costo neto por litro, sin IVA          (en el Excel: H14 = H11 ÷ 1,16 − H13)
    """
    litros = Decimal(litros or 0)
    if not litros:
        return Decimal(0), Decimal(0)
    return Decimal(total or 0) / litros, Decimal(neto or 0) / litros


def neto_viaje(flete, descuento):
    """Costos varios!E6 = Flete − Descuento. Es la base de los impuestos y de lo facturado por dominio."""
    return Decimal(flete or 0) - Decimal(descuento or 0)


def impuestos_del_mes(neto_mes, par):
    """Costos varios: IIBB 2 %, tasa municipal 0,2 % y ganancias 6 % sobre el neto facturado del mes (E6)."""
    neto_mes = Decimal(neto_mes or 0)
    return [
        (f'Ingresos brutos ({_pct(par.par_iibb)})', neto_mes * par.par_iibb / 100),
        (f'Tasa municipal ({_pct(par.par_muni)})', neto_mes * par.par_muni / 100),
        (f'Ganancias ({_pct(par.par_gana)})', neto_mes * par.par_gana / 100),
    ]


def litros_cada_100km(litros, km_reales):
    """
    Combustible → Prom.Comb del Excel. En GeneXus (CalcICa): cax_prom = cax_tcom / cax_kmre * 100.
    litros = rec_suml del recorrido; km_reales = rec_tkms.
    """
    km_reales = Decimal(km_reales or 0)
    if not km_reales:
        return Decimal(0)
    return (Decimal(litros or 0) / km_reales * 100).quantize(Decimal('0.01'))


def km_reales_por_viaje(viajes):
    """
    Combustible → Km Reales del Excel, llevado a cada viaje.
    Los km reales del recorrido (rec_tkms) se reparten entre sus viajes según los km cargados (via_kcar).
    Un viaje sin recorrido cuenta sus km cargados.
    Devuelve {via_codi: km}.
    """
    km = {}
    por_recorrido = defaultdict(list)
    for v in viajes:
        if v.rec_codi_id:
            por_recorrido[v.rec_codi_id].append(v)
        else:
            km[v.via_codi] = Decimal(v.via_kcar or 0)
    for lista in por_recorrido.values():
        resto = Decimal(lista[0].rec_codi.rec_tkms or 0)
        base = sum((Decimal(v.via_kcar or 0) for v in lista), Decimal(0))
        for v in lista:
            km[v.via_codi] = resto * (Decimal(v.via_kcar or 0) / base if base else Decimal(1) / len(lista))
    return km


def cubiertas_por_km(camion, costo_tipo):
    """
    Costos por dominio!H = VLOOKUP(LINEAL, CUB, 5) × E + VLOOKUP(TACO, CUB, 5) × F + VLOOKUP(CARRETON, CUB, 5) × G
    costo_tipo: {1: $/km lineal, 2: $/km taco, 3: $/km carretón}, cada uno = precio ÷ duración (Costos variables!G19:G21).
    """
    if camion is None:
        return Decimal(0)
    return (costo_tipo.get(1, Decimal(0)) * camion.cam_clin
            + costo_tipo.get(2, Decimal(0)) * camion.cam_ctac
            + costo_tipo.get(3, Decimal(0)) * camion.cam_ccar)


def cubiertas_servicio_por_km(servicio, costo_tipo):
    """
    Costos variables!D24:D27 ("Costo cubiertas" por tipo de equipo) = Σ cantidad de cubiertas × $/km del tipo.
      CARRETON 12 carretón · CAMILLA 6 lineal + 4 taco · BITREN 24 lineal · BATEA 12 lineal (L24:P27).
    Costos Totales!B10 multiplica esto por los km del viaje (Det.Via.Nov[Kms]).
    """
    if servicio is None:
        return Decimal(0)
    return (costo_tipo.get(1, Decimal(0)) * servicio.tse_clin
            + costo_tipo.get(2, Decimal(0)) * servicio.tse_ctac
            + costo_tipo.get(3, Decimal(0)) * servicio.tse_ccar)


def repartir_por_km(total, km_por_clave):
    """Sueldo de un chofer repartido entre los camiones que manejó según sus km (Costos por dominio!BM4:CF18)."""
    base = sum(km_por_clave.values(), Decimal(0))
    if not base:
        return {}
    return {k: Decimal(total) * km / base for k, km in km_por_clave.items()}


def costo_por_km(precio, km_duracion):
    """Costos variables!G19 = E19 ÷ F19 (cubiertas) y F30 = E30 ÷ D30 (service)."""
    if not precio or not km_duracion:
        return Decimal(0)
    return Decimal(precio) / Decimal(km_duracion)


def service_por_km(modelo):
    """Costos por dominio!I = VLOOKUP(MODELO, SERVICE, 4): $ del service ÷ km de duración."""
    if modelo is None:
        return Decimal(0)
    return costo_por_km(modelo.mod_isvc, modelo.mod_kdur)


def valor_en_pesos(camion, cotizacion):
    """Costos variables!F37 = E37 × C16 (U$S × cotización)."""
    return Decimal(camion.cam_vusd or 0) * Decimal(cotizacion or 0)


def sueldo_variable(sueldo, par):
    """Sueldos!U = $ KM REC × KM REC + $ KM ANCHO × KM ANCHO (los $/km están en Parametros)."""
    return par.par_kmre * sueldo.sue_kmre + par.par_kman * sueldo.sue_kman


def amortizacion_mensual(valor, vida_util_meses):
    """
    Costos variables → amortización: valor del camión y equipo ÷ vida útil en meses.
    En el Excel, Costos Totales!B11 apunta a 'Costos Totales'!G38, que está vacía; acá se calcula por dominio.
    """
    if not valor or not vida_util_meses:
        return Decimal(0)
    return Decimal(valor) / Decimal(vida_util_meses)


def fecha_de_cobro(total, cobros):
    """
    Nuevo: fecha en que la suma de los cobros alcanza el total de la factura; None si todavía se debe.
    cobros: lista de (fecha, importe).
    """
    acumulado = Decimal(0)
    for fecha, importe in sorted((c for c in cobros if c[0]), key=lambda c: c[0]):
        acumulado += Decimal(importe or 0)
        if acumulado >= Decimal(total or 0) - Decimal('0.01'):
            return fecha
    return None


#--------------------------------------------------------AUXILIARES↓-----------------------------------------------------------------

def parametros_vigentes(mes, parametros, por_defecto):
    """Último registro de Parametros con par_desd <= fin del mes. parametros viene ordenado por par_desd."""
    fin = fin_de_mes(mes)
    vigente = por_defecto
    for p in parametros:
        if p.par_desd <= fin:
            vigente = p
    return vigente


def primero_de_mes(d):
    return date(d.year, d.month, 1)


def fin_de_mes(d):
    siguiente = date(d.year + d.month // 12, d.month % 12 + 1, 1)
    return siguiente - timedelta(days=1)


def sumar_meses(d, n):
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def meses_entre(desde, hasta):
    m = primero_de_mes(desde)
    while m <= hasta:
        yield m
        m = date(m.year + m.month // 12, m.month % 12 + 1, 1)


def _pct(v):
    return f"{Decimal(v).normalize():f}".replace('.', ',') + '%'
