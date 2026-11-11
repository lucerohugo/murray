'use client';
import { useMemo } from 'react';
import { useDatos } from '@/components/Providers';
import { ChartBox, css, ejeMoney, segmento, sinGrilla } from '@/components/ChartBox';
import { Delta, Empty, Kpis, Legend, Panel, Pill, ViewHead } from '@/components/ui';
import { AGING, tripOk, type Factura } from '@/lib/engine';
import { fd, fdl } from '@/lib/dates';
import { money, moneyM, n0, pct, short } from '@/lib/format';

const sum = (a: Factura[]) => a.reduce((s, x) => s + x.total, 0);

export default function Cobranzas() {
  const { ds, eng, F, prev } = useDatos();
  const [pa, pb] = prev;

  const d = useMemo(() => {
    const ok = tripOk(F);
    const cart = eng.cartera(F.hasta, F), cp = eng.cartera(pb, F), tot = sum(cart);
    const venc = sum(cart.filter(x => x.atraso > 0)), m60 = sum(cart.filter(x => x.atraso > 60));
    const v90 = ds.viajes.filter(t => t.emision > F.hasta - 90 && t.emision <= F.hasta && ok(t)).reduce((s, t) => s + t.total, 0) / 90;
    const cob = ds.viajes.filter(t => t.cobro !== null && t.cobro >= F.desde && t.cobro <= F.hasta && ok(t)).reduce((s, t) => s + t.total, 0);
    const cobp = ds.viajes.filter(t => t.cobro !== null && t.cobro >= pa && t.cobro <= pb && ok(t)).reduce((s, t) => s + t.total, 0);
    const by: Record<string, number[]> = {};
    cart.forEach(x => { (by[x.cliente] ??= [0, 0, 0, 0])[AGING.findIndex(a => a[1](x))] += x.total; });
    const top = Object.entries(by).sort((a, b) => b[1].reduce((s, v) => s + v) - a[1].reduce((s, v) => s + v)).slice(0, 10);
    const mi = Math.max(0, eng.monthIdx(F.hasta)), Ms = ds.meses.slice(0, mi + 1);
    const pts = Ms.map(M => Math.min(M.end, F.hasta, ds.hoy));
    const saldo = pts.map(x => sum(eng.cartera(x, F)));
    return { cart, cp, tot, venc, m60, v90, cob, cobp, top, Ms, pts, saldo, rows: [...cart].sort((a, b) => b.atraso - a.atraso) };
  }, [ds, eng, F, pa, pb]);
  const { tot, top, rows } = d;

  return (
    <>
      <ViewHead slug="cobranzas" />
      <Kpis items={[
        ['Plata en la calle', moneyM(tot), <Delta a={tot} b={sum(d.cp)} inv />, true],
        ['Vencido', moneyM(d.venc), `${pct(d.venc / tot)} del saldo`],
        ['A vencer', moneyM(tot - d.venc)],
        ['Más de 60 días', <span className={d.m60 / tot > 0.15 ? 'down' : ''}>{moneyM(d.m60)}</span>, `${pct(d.m60 / tot)} del saldo`],
        ['Días de calle', n0(tot / (d.v90 || 1)), 'Días de facturación sin cobrar'],
        ['Cobrado en el período', moneyM(d.cob), <Delta a={d.cob} b={d.cobp} />],
      ]} />
      <section className="grid">
        <Panel id="c-aging" span={8} title="Antigüedad de la deuda por cliente" note='Saldo pendiente a la fecha "hasta", según los días de vencida cada factura.'>
          <Legend items={AGING.map(([n, , k]) => [n, k] as [string, string])} />
          <ChartBox label="Antigüedad de la deuda por cliente" type="bar" height={400} data={{
            labels: top.map(x => short(x[0])),
            datasets: AGING.map(([n, , k], i) => ({ label: n, data: top.map(x => x[1][i]), ...segmento(css(k)), borderWidth: { right: 2 }, maxBarThickness: 20 })),
          }} options={{
            indexAxis: 'y', scales: { x: { ...ejeMoney(), stacked: true }, y: { ...sinGrilla, stacked: true } },
            plugins: { tooltip: { callbacks: { title: (i: any[]) => top[i[0].dataIndex][0], label: (t: any) => `${t.dataset.label}: ${moneyM(t.raw)}` } } },
          }} />
        </Panel>
        <Panel id="c-saldo" span={4} title="Saldo en la calle" note="Pendiente de cobro al cierre de cada mes.">
          <ChartBox label="Saldo en la calle" type="line" height={400} data={{
            labels: d.Ms.map(M => M.label),
            datasets: [{ data: d.saldo, borderColor: css('--s2'), backgroundColor: css('--s2') + '26', fill: true, borderWidth: 2, pointRadius: 2, tension: 0.25 }],
          }} options={{
            scales: { y: { ...ejeMoney(), beginAtZero: true }, x: { ...sinGrilla, ticks: { maxTicksLimit: 6 } } },
            plugins: { tooltip: { callbacks: { title: (i: any[]) => 'Al ' + fdl(d.pts[i[0].dataIndex]), label: (t: any) => moneyM(t.raw) } } },
          }} />
        </Panel>
        <Panel id="c-fact" span={12} title="Facturas pendientes" note="Ordenadas por días de atraso.">
          <div className="tbl" style={{ maxHeight: 440 }}>
            <table>
              {rows.length ? <>
                <thead><tr><th>Factura</th><th>Cliente</th><th>Emisión</th><th>Vence</th><th className="n">Días de atraso</th><th className="n">Monto con IVA</th><th>Estado</th></tr></thead>
                <tbody>{rows.slice(0, 300).map(x => {
                  const a = AGING.findIndex(g => g[1](x));
                  return (
                    <tr key={x.factura}><td className="n" style={{ textAlign: 'left' }}>{x.factura}</td><td>{x.cliente}</td><td>{fd(x.emision)}</td><td>{fd(x.vence)}</td>
                      <td className="n">{x.atraso > 0 ? x.atraso : '–'}</td><td className="n">{money(x.total)}</td>
                      <td><Pill k={a === 0 ? '' : a >= 2 ? 'bad' : 'warn'}>{AGING[a][0]}</Pill></td></tr>
                  );
                })}</tbody>
                <tfoot><tr><th colSpan={5}>{n0(rows.length)} facturas pendientes</th><th className="n">{moneyM(tot)}</th><th /></tr></tfoot>
              </> : <Empty>No hay facturas pendientes con estos filtros.</Empty>}
            </table>
          </div>
        </Panel>
      </section>
    </>
  );
}
