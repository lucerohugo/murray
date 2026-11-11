'use client';
import { useMemo, useState } from 'react';
import { useDatos } from '@/components/Providers';
import { ChartBox, barra, css, ejeMoney, ejeNum, sinGrilla } from '@/components/ChartBox';
import { Delta, Empty, Kpis, Legend, Panel, Pill, Plate, ViewHead } from '@/components/ui';
import { dd, fd } from '@/lib/dates';
import { money, moneyM, n0, n1, pct, short } from '@/lib/format';

const DOW = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

export default function Viajes() {
  const { ds, eng, F, prev } = useDatos();
  const [q, setQ] = useState('');
  const [pa, pb] = prev;

  const d = useMemo(() => {
    const c = eng.calc(F.desde, F.hasta, F), p = eng.calc(pa, pb, F), T = c.trips;
    const B = eng.buckets(F.desde, F.hasta), S = B.map(x => T.filter(t => t.fecha >= x.a && t.fecha <= x.b));
    const cnt = Array(7).fill(0), days = Array(7).fill(0);
    for (let x = F.desde; x <= F.hasta; x++) days[(dd(x).getUTCDay() + 6) % 7]++;
    T.forEach(t => cnt[(dd(t.fecha).getUTCDay() + 6) % 7]++);
    const sv = ds.servicios.map(s => {
      const ts = T.filter(t => t.servicio === s), km = ts.reduce((a, t) => a + t.kmReal, 0);
      const cost = ts.reduce((a, t) => a + t.kmReal * c.C.U[t.unidad].costoKm, 0);
      return { s, n: ts.length, fact: ts.reduce((a, t) => a + t.neto, 0), km, cost };
    }).filter(x => x.n);
    const cl: Record<string, { f: number; c: number; n: number }> = {};
    T.forEach(t => { const o = (cl[t.cliente] ??= { f: 0, c: 0, n: 0 }); o.f += t.neto; o.c += t.kmReal * c.C.U[t.unidad].costoKm; o.n++; });
    const top = Object.entries(cl).sort((a, b) => b[1].f - a[1].f).slice(0, 8);
    const rt: Record<string, { n: number; km: number; f: number }> = {};
    T.forEach(t => { const o = (rt[`${t.origen} → ${t.destino}`] ??= { n: 0, km: 0, f: 0 }); o.n++; o.km += t.kmCargado; o.f += t.neto; });
    const rutas = Object.entries(rt).sort((a, b) => b[1].n - a[1].n).slice(0, 25);
    return { c, p, T, B, S, cnt, days, sv, top, rutas };
  }, [ds, eng, F, pa, pb]);
  const { c, p, T, B, S, sv, top, rutas } = d;

  const rows = useMemo(() => {
    const s = q.trim().toLowerCase();
    return T.filter(t => !s || [t.cliente, t.chofer, t.unidad, t.origen, t.destino, t.servicio, t.factura].join(' ').toLowerCase().includes(s)).slice().reverse();
  }, [T, q]);
  const sum = (k: 'kmCargado' | 'flete' | 'descuento' | 'neto') => rows.reduce((s, t) => s + t[k], 0);
  const rmax = rutas.length ? rutas[0][1].n : 1;

  return (
    <>
      <ViewHead slug="viajes" />
      <Kpis items={[
        ['Viajes', n0(T.length), <Delta a={T.length} b={p.trips.length} />, true],
        ['Km cargados', n0(c.kmc), <Delta a={c.kmc} b={p.kmc} />],
        ['Km vacíos', pct((c.km - c.kmc) / c.km), `${n0(c.km - c.kmc)} km sin carga`],
        ['Facturación promedio por viaje', money(c.fact / (T.length || 1)), <Delta a={c.fact / T.length} b={p.fact / p.trips.length} />],
        ['Ingreso por km', `${money(c.fact / (c.km || 1))}`, `${money(c.fact / (c.kmc || 1))} por km cargado`],
        ['Descuentos', moneyM(c.desc), `${pct(c.desc / c.flete)} del flete`],
      ]} />
      <section className="grid">
        <Panel id="o-evol" span={8} title="Facturación y viajes en el tiempo" note="Pasá el mouse para ver la cantidad de viajes de cada tramo.">
          <ChartBox label="Facturación en el tiempo" type="bar" data={{
            labels: B.map(x => x.l), datasets: [{ data: S.map(s => s.reduce((a, t) => a + t.neto, 0)), backgroundColor: css('--s1'), ...barra({ maxBarThickness: 18 }) }],
          }} options={{
            scales: { y: ejeMoney(), x: { ...sinGrilla, ticks: { maxTicksLimit: 16 } } },
            plugins: { tooltip: { callbacks: { label: (x: any) => `${moneyM(x.raw)} · ${S[x.dataIndex].length} viajes` } } },
          }} />
        </Panel>
        <Panel id="o-dow" span={4} title="Viajes por día de la semana" note="Promedio de viajes por día.">
          <ChartBox label="Viajes por día de la semana" type="bar" data={{
            labels: DOW, datasets: [{ data: d.cnt.map((v, i) => (d.days[i] ? v / d.days[i] : 0)), backgroundColor: css('--s1'), ...barra() }],
          }} options={{
            scales: { y: ejeNum(), x: sinGrilla },
            plugins: { tooltip: { callbacks: { label: (x: any) => `${n1(x.raw)} viajes por día · ${d.cnt[x.dataIndex]} en total` } } },
          }} />
        </Panel>
        <Panel id="o-serv" span={7} title="Ingreso contra costo por servicio" note="Los dos medidos por km recorrido, con la vuelta vacía incluida.">
          <Legend items={[['Ingreso por km', '--s1'], ['Costo por km', '--s2']]} />
          <ChartBox label="Ingreso contra costo por servicio" type="bar" data={{
            labels: sv.map(x => x.s), datasets: [
              { label: 'Ingreso', data: sv.map(x => x.fact / x.km), backgroundColor: css('--s1'), ...barra() },
              { label: 'Costo', data: sv.map(x => x.cost / x.km), backgroundColor: css('--s2'), ...barra() },
            ],
          }} options={{
            scales: { y: { ...ejeNum(), ticks: { callback: (v: number) => '$' + n0(v) } }, x: sinGrilla },
            plugins: { tooltip: { callbacks: {
              label: (x: any) => `${x.dataset.label}: ${money(x.raw)}/km`,
              footer: (i: any[]) => { const s = sv[i[0].dataIndex]; return `${s.n} viajes · margen ${pct((s.fact - s.cost) / s.fact)}`; },
            } } },
          }} />
        </Panel>
        <Panel id="o-cli" span={5} title="Facturación por cliente" note="Top 8 por facturación neta.">
          <ChartBox label="Facturación por cliente" type="bar" data={{
            labels: top.map(x => short(x[0])), datasets: [{ data: top.map(x => x[1].f), backgroundColor: css('--s3'), ...barra() }],
          }} options={{
            indexAxis: 'y', scales: { x: ejeMoney(), y: sinGrilla },
            plugins: { tooltip: { callbacks: {
              title: (i: any[]) => top[i[0].dataIndex][0],
              label: (x: any) => { const o = top[x.dataIndex][1]; return [`${moneyM(o.f)} en ${o.n} viajes`, `Margen estimado ${pct((o.f - o.c) / o.f)}`]; },
            } } },
          }} />
        </Panel>
        <Panel id="o-rutas" span={12} title="Rutas más frecuentes" note="Origen → destino, de mayor a menor cantidad de viajes.">
          <div className="tbl" style={{ maxHeight: 360 }}>
            <table>
              {rutas.length ? <>
                <thead><tr><th>Ruta</th><th className="n">Viajes</th><th style={{ width: '20%' }} /><th className="n">Km promedio</th><th className="n">Ingreso por km</th><th className="n">Facturación</th></tr></thead>
                <tbody>{rutas.map(([k, o]) => (
                  <tr key={k}><td>{k}</td><td className="n">{o.n}</td><td><span className="bar-inline" style={{ width: `${(o.n / rmax) * 100}%` }} /></td>
                    <td className="n">{n0(o.km / o.n)}</td><td className="n">{money(o.f / o.km)}</td><td className="n">{moneyM(o.f)}</td></tr>
                ))}</tbody>
              </> : <Empty>Sin viajes con estos filtros.</Empty>}
            </table>
          </div>
        </Panel>
        <Panel id="o-viajes" span={12} title="Detalles viajes" note="Buscá por cliente, chofer, patente o localidad. Se muestran hasta 300 filas.">
          <input className="search" type="search" placeholder="Buscar…" aria-label="Buscar viajes" value={q} onChange={e => setQ(e.target.value)} />
          <div className="tbl" style={{ maxHeight: 440 }}>
            <table>
              <thead><tr><th>Fecha</th><th>Origen → Destino</th><th>Cliente</th><th>Chofer</th><th>Dominio</th><th>Servicio</th><th className="n">Km</th><th className="n">Flete</th><th className="n">Desc.</th><th className="n">Neto</th><th>Cobro</th></tr></thead>
              <tbody>{rows.slice(0, 300).map(t => (
                <tr key={t.id}><td>{fd(t.fecha)}</td><td>{t.origen} → {t.destino}</td><td>{t.cliente}</td><td>{t.chofer}</td><td><Plate p={t.unidad} /></td><td>{t.servicio}</td>
                  <td className="n">{n0(t.kmCargado)}</td><td className="n">{money(t.flete)}</td><td className="n">{t.descuento ? money(t.descuento) : '–'}</td><td className="n">{money(t.neto)}</td>
                  <td>{t.cobro !== null && t.cobro <= F.hasta ? <Pill k="ok">Cobrado</Pill> : F.hasta > t.vence ? <Pill k="bad">Vencido</Pill> : <Pill>A vencer</Pill>}</td></tr>
              ))}</tbody>
              <tfoot><tr><th colSpan={6}>{n0(rows.length)} viajes</th><th className="n">{n0(sum('kmCargado'))}</th><th className="n">{moneyM(sum('flete'))}</th><th className="n">{moneyM(sum('descuento'))}</th><th className="n">{moneyM(sum('neto'))}</th><th /></tr></tfoot>
            </table>
          </div>
        </Panel>
      </section>
    </>
  );
}
