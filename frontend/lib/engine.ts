/* =====================================================================
   MOTOR DE CÁLCULO
   Replica las fórmulas de la PLANILLA COSTO MAYO (ver lib/origen.ts).
   ===================================================================== */
import type { Dataset, Filtros, RawUnidad, Rubro, Viaje } from './types';
import { dd } from './dates';

export const RUBROS: Rubro[] = ['Combustible', 'Choferes (fijo)', 'Choferes (por km)', 'Administración', 'Gastos generales', 'Impuestos',
  'Amortización', 'Mantenimiento', 'Cubiertas', 'Service', 'Seguros', 'Patente y rentas'];
export const VARIABLES = new Set<string>(['Combustible', 'Choferes (por km)', 'Impuestos', 'Cubiertas', 'Service']);
export const GRUPOS: [string, Rubro[]][] = [
  ['Combustible', ['Combustible']],
  ['Personal', ['Choferes (fijo)', 'Choferes (por km)', 'Administración']],
  ['Mantenimiento y desgaste', ['Mantenimiento', 'Cubiertas', 'Service']],
  ['Amortización y seguros', ['Amortización', 'Seguros', 'Patente y rentas']],
  ['Estructura e impuestos', ['Gastos generales', 'Impuestos']],
];
export const GRUPO_COLOR = ['--s1', '--s2', '--s3', '--s4', '--s5'];

export type Montos = Partial<Record<string, number>>;
export interface UnidadCalc {
  u: RawUnidad; r: Montos; all: Montos; km: number; kmc: number; viajes: number; fact: number; litros: number;
  direct: number; total: number; costoKm: number; factKm: number; neto: number; parada: boolean;
}
export interface Costos { U: Record<string, UnidadCalc>; est: Montos; kmTot: number }
export interface Calc {
  a: number; b: number; C: Costos; trips: Viaje[]; rub: Montos; costo: number; variable: number; fact: number; flete: number; desc: number;
  km: number; kmc: number; kmCost: number; res: number; units: UnidadCalc[]; tripOnly: boolean; litros: number;
}
export interface Factura extends Viaje { atraso: number }

export const sumM = (o: Montos) => Object.values(o).reduce<number>((s, v) => s + (v ?? 0), 0);

export const tripOk = (F: Filtros) => (t: Viaje) =>
  (!F.empresa || t.empresa === F.empresa) && (!F.servicio || t.servicio === F.servicio) && (!F.unidad || t.unidad === F.unidad) &&
  (!F.chofer || t.chofer === F.chofer) && (!F.cliente || t.cliente === F.cliente);
export const unitOk = (F: Filtros) => (u: RawUnidad) =>
  (!F.servicio || u.servicio === F.servicio) && (!F.unidad || u.id === F.unidad) && (!F.chofer || u.chofer === F.chofer);

export function createEngine(ds: Dataset) {
  const gmBy = ds.meses.map((_, m) => ds.gastosMes.filter(g => g.mes === m));
  const memo = new Map<string, Costos>();
  const monthIdx = (d: number) => ds.meses.findIndex(M => d >= M.start && d <= M.end);

  /** Costos de todas las unidades en [a,b], sin filtros. Equivale a la hoja "Costos por dominio" para ese rango. */
  function costs(a: number, b: number): Costos {
    const k = `${a}|${b}`;
    const hit = memo.get(k); if (hit) return hit;
    const U: Record<string, UnidadCalc> = {};
    ds.unidades.forEach(u => (U[u.id] = { u, r: {}, all: {}, km: 0, kmc: 0, viajes: 0, fact: 0, litros: 0, direct: 0, total: 0, costoKm: 0, factKm: 0, neto: 0, parada: true }));
    const est: Montos = {};
    const add = (id: string | null, rub: string, v: number) => {
      const o = id && U[id] ? U[id].r : est;
      o[rub] = (o[rub] ?? 0) + v;
    };
    // gastos mensuales: se prorratean por día del mes (Adaptado)
    ds.meses.forEach((M, m) => {
      const ov = Math.min(b, M.end) - Math.max(a, M.start) + 1;
      if (ov > 0) { const f = ov / M.days; gmBy[m].forEach(g => add(g.unidad, g.rubro, g.monto * f)); }
    });
    ds.gastosDia.forEach(g => {
      if (g.fecha >= a && g.fecha <= b) { add(g.unidad, g.rubro, g.monto); if (g.litros && g.unidad && U[g.unidad]) U[g.unidad].litros += g.litros; }
    });
    // cubiertas y service: $/km × km reales (COSTOS.DOM U, I)
    ds.viajes.forEach(t => {
      if (t.fecha < a || t.fecha > b || !U[t.unidad]) return;
      const x = U[t.unidad];
      x.km += t.kmReal; x.kmc += t.kmCargado; x.viajes++; x.fact += t.neto;
      add(t.unidad, 'Cubiertas', t.kmReal * t.costoCubKm);
      add(t.unidad, 'Service', t.kmReal * t.costoServiceKm);
    });
    const kmTot = Object.values(U).reduce((s, x) => s + x.km, 0);
    Object.values(U).forEach(x => {
      x.direct = sumM(x.r); x.all = { ...x.r };
      // estructura (admin, varios, impuestos) ÷ km totales × km de la unidad — Costos varios!G4 y C27
      if (x.km && kmTot) Object.entries(est).forEach(([r, v]) => (x.all[r] = (x.all[r] ?? 0) + (v ?? 0) * x.km / kmTot));
      x.total = sumM(x.all);
      x.costoKm = x.km ? x.total / x.km : 0;          // COSTOS.DOM[TOTAL X KM]
      x.factKm = x.km ? x.fact / x.km : 0;            // NETO.X.DOM[FACTURADO X DOM X KM]
      x.neto = x.fact - x.total;                      // NETO.X.DOM[NETO X DOM]
      x.parada = !x.viajes;                           // TOTAL DOM PARADO
    });
    const res = { U, est, kmTot };
    memo.set(k, res);
    return res;
  }

  /** Totales del rango con los filtros aplicados. */
  function calc(a: number, b: number, F: Filtros): Calc {
    const C = costs(a, b), ok = tripOk(F), uok = unitOk(F);
    const trips = ds.viajes.filter(t => t.fecha >= a && t.fecha <= b && ok(t));
    const tripOnly = !!(F.empresa || F.cliente);
    const rub: Montos = {};
    const addR = (o: Montos, f: number) => Object.entries(o).forEach(([r, v]) => (rub[r] = (rub[r] ?? 0) + (v ?? 0) * f));
    if (!tripOnly) {
      const any = F.servicio || F.unidad || F.chofer;
      Object.values(C.U).forEach(x => { if (uok(x.u)) addR(x.all, 1); });
      if (!any && !C.kmTot) addR(C.est, 1);
    } else {
      // filtro por cliente/razón social: km reales × costo por km de la unidad (Adaptado)
      const kmU: Record<string, number> = {};
      trips.forEach(t => (kmU[t.unidad] = (kmU[t.unidad] ?? 0) + t.kmReal));
      Object.entries(kmU).forEach(([id, km]) => addR(C.U[id].all, km / C.U[id].km));
    }
    const costo = sumM(rub);
    const variable = Object.entries(rub).filter(([r]) => VARIABLES.has(r)).reduce((s, [, v]) => s + (v ?? 0), 0);
    const fact = trips.reduce((s, t) => s + t.neto, 0), flete = trips.reduce((s, t) => s + t.flete, 0);
    const km = trips.reduce((s, t) => s + t.kmReal, 0), kmc = trips.reduce((s, t) => s + t.kmCargado, 0);
    const units = Object.values(C.U).filter(x => uok(x.u));
    return {
      a, b, C, trips, rub, costo, variable, fact, flete, desc: flete - fact, km, kmc,
      kmCost: tripOnly ? km : units.reduce((s, x) => s + x.km, 0), res: fact - costo, units, tripOnly,
      litros: units.reduce((s, x) => s + x.litros, 0),
    };
  }

  /** Facturas emitidas hasta asOf y no cobradas a esa fecha (Nuevo). */
  function cartera(asOf: number, F: Filtros): Factura[] {
    const ok = tripOk(F);
    return ds.viajes.filter(t => t.emision <= asOf && (t.cobro === null || t.cobro > asOf) && ok(t)).map(t => ({ ...t, atraso: asOf - t.vence }));
  }

  /** Tramos para los gráficos: día (≤ 62 días), semana (≤ 190) o mes. */
  function buckets(a: number, b: number) {
    const n = b - a + 1, out: { a: number; b: number; l: string }[] = [];
    if (n <= 62) for (let d = a; d <= b; d++) { const x = dd(d); out.push({ a: d, b: d, l: `${x.getUTCDate()}/${x.getUTCMonth() + 1}` }); }
    else if (n <= 190) for (let d = a; d <= b; d += 7) { const x = dd(d); out.push({ a: d, b: Math.min(b, d + 6), l: `sem ${x.getUTCDate()}/${x.getUTCMonth() + 1}` }); }
    else ds.meses.forEach(M => { if (M.end >= a && M.start <= b) out.push({ a: Math.max(a, M.start), b: Math.min(b, M.end), l: M.label }); });
    return out;
  }

  return { costs, calc, cartera, buckets, monthIdx };
}
export type Engine = ReturnType<typeof createEngine>;

export const AGING: [string, (x: Factura) => boolean, string][] = [
  ['A vencer', x => x.atraso <= 0, '--s3'],
  ['1–30 días', x => x.atraso > 0 && x.atraso <= 30, '--s4'],
  ['31–60 días', x => x.atraso > 30 && x.atraso <= 60, '--s2'],
  ['Más de 60', x => x.atraso > 60, '--bad'],
];
