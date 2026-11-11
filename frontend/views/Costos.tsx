'use client';
import { useMemo } from 'react';
import { useDatos } from '@/components/Providers';
import { ChartBox, barra, css, ejeMoney, ejeNum, segmento, sinGrilla } from '@/components/ChartBox';
import { Delta, Kpis, Legend, Panel, Split, ViewHead } from '@/components/ui';
import { GRUPOS, GRUPO_COLOR, RUBROS, VARIABLES } from '@/lib/engine';
import { money, moneyM, n0, n1, pct } from '@/lib/format';

export default function Costos() {
  const { ds, eng, F, prev } = useDatos();
  const [pa, pb] = prev;

  const d = useMemo(() => {
    const c = eng.calc(F.desde, F.hasta, F), p = eng.calc(pa, pb, F), mi = Math.max(0, eng.monthIdx(F.hasta)), g = ds.gasoil[mi];
    const rb = RUBROS.map(r => [r, c.rub[r] ?? 0] as [string, number]).sort((a, b) => b[1] - a[1]);
    const B = eng.buckets(F.desde, F.hasta), S = B.map(x => eng.calc(x.a, x.b, F));
    // gastos de estructura del rango (prorrateados por día) y la parte que le toca a la selección
    const es: Record<string, number> = {};
    ds.meses.forEach((M, m) => {
      const ov = Math.min(F.hasta, M.end) - Math.max(F.desde, M.start) + 1;
      if (ov > 0) ds.gastosMes.filter(x => x.mes === m && !x.unidad).forEach(x => { const k = `${x.rubro}|${x.concepto}`; es[k] = (es[k] ?? 0) + (x.monto * ov) / M.days; });
    });
    const share = c.tripOnly ? c.km / (c.C.kmTot || 1) : F.servicio || F.unidad || F.chofer ? c.units.reduce((s, x) => s + x.km, 0) / (c.C.kmTot || 1) : 1;
    const E = Object.entries(es).map(([k, v]) => { const [r, n] = k.split('|'); return [r, n, v * share] as [string, string, number]; }).sort((a, b) => b[2] - a[2]);
    return { c, p, mi, g, rb, B, S, E, share };
  }, [ds, eng, F, pa, pb]);
  const { c, p, g, rb, B, S, E } = d;
  const kmc = c.kmCost || 1;
  const emax = E.length ? E[0][2] : 1, etot = E.reduce((s, x) => s + x[2], 0);
  const Ms = ds.meses.slice(0, d.mi + 1);

  return (
    <>
      <ViewHead slug="costos" />
      <Kpis items={[
        ['Costo total', moneyM(c.costo), <Delta a={c.costo} b={p.costo} inv />, true],
        ['Costo fijo', moneyM(c.costo - c.variable), `${pct(1 - c.variable / c.costo)} del total`],
        ['Costo variable', moneyM(c.variable), `${pct(c.variable / c.costo)} del total`],
        ['Costo por km', `${money(c.costo / kmc)}`, <Delta a={c.costo / c.kmCost} b={p.costo / p.kmCost} inv />],
        ['Gasoil por litro', `${money(g.final)}`, `Costo final de ${ds.meses[d.mi].label}`],
        ['Litros cargados', n0(c.litros), <Delta a={c.litros} b={p.litros} inv />],
      ]} />
      <section className="grid">
        <Panel id="g-rub" span={7} title="Costos totales por rubro" note="De mayor a menor. Pasá el mouse para ver el peso de cada rubro.">
          <ChartBox label="Costos totales por rubro" type="bar" height={360} data={{
            labels: rb.map(x => x[0]),
            datasets: [{ data: rb.map(x => x[1]), backgroundColor: rb.map(x => (VARIABLES.has(x[0]) ? css('--s2') : css('--s1'))), ...barra({ maxBarThickness: 18 }) }],
          }} options={{
            indexAxis: 'y', scales: { x: ejeMoney(), y: sinGrilla },
            plugins: { tooltip: { callbacks: {
              label: (t: any) => `${moneyM(t.raw)} · ${pct(t.raw / c.costo)} · ${money(t.raw / kmc)}/km`,
              footer: (i: any[]) => (VARIABLES.has(rb[i[0].dataIndex][0]) ? 'Variable' : 'Fijo'),
            } } },
          }} />
        </Panel>
        <Panel id="g-split" span={5} title="Fijo contra variable" note="Variable = se mueve con los km o con lo facturado. Fijo = se paga aunque el camión no salga.">
          <Split variable={c.variable / c.costo} />
          <dl className="kv">
            <dt style={{ fontWeight: 600, color: 'var(--ink)' }}>Rubro</dt><dd style={{ fontWeight: 600, color: 'var(--ink)' }}>$/km</dd><dd style={{ fontWeight: 600, color: 'var(--ink)' }}>Tipo</dd>
            {rb.map(([r, v]) => (
              <span key={r} style={{ display: 'contents' }}>
                <dt><span className="sw" style={{ background: `var(${VARIABLES.has(r) ? '--s2' : '--s1'})` }} />{r}</dt>
                <dd>{money(v / kmc)}</dd><dd>{VARIABLES.has(r) ? 'Variable' : 'Fijo'}</dd>
              </span>
            ))}
          </dl>
        </Panel>
        <Panel id="g-evol" span={8} title="Evolución por bloque" note="Costo de cada tramo, apilado por bloque.">
          <Legend items={GRUPOS.map(([n], i) => [n, GRUPO_COLOR[i]] as [string, string])} />
          <ChartBox label="Evolución del costo por bloque" type="bar" data={{
            labels: B.map(x => x.l),
            datasets: GRUPOS.map(([n, rs], i) => ({ label: n, data: S.map(s => rs.reduce((a, r) => a + (s.rub[r] ?? 0), 0)), ...segmento(css(GRUPO_COLOR[i])) })),
          }} options={{
            scales: { x: { ...sinGrilla, stacked: true, ticks: { maxTicksLimit: 16 } }, y: { ...ejeMoney(), stacked: true } },
            plugins: { tooltip: { mode: 'index', intersect: false, callbacks: {
              label: (t: any) => `${t.dataset.label}: ${moneyM(t.raw)}`,
              footer: (i: any[]) => `Total ${moneyM(i.reduce((s, t) => s + t.raw, 0))}`,
            } } },
          }} />
        </Panel>
        <Panel id="g-gas" span={4} title="Precio del gasoil" note="Precio de lista contra costo final por litro.">
          <Legend items={[['Facturado', '--ink-3'], ['Costo final', '--s1']]} />
          <ChartBox label="Precio del gasoil" type="line" height={200} data={{
            labels: Ms.map(M => M.label), datasets: [
              { label: 'Facturado', data: ds.gasoil.slice(0, d.mi + 1).map(x => x.lista), borderColor: css('--ink-3'), borderDash: [4, 4], borderWidth: 2, pointRadius: 0 },
              { label: 'Final', data: ds.gasoil.slice(0, d.mi + 1).map(x => x.final), borderColor: css('--s1'), backgroundColor: css('--s1'), borderWidth: 2, pointRadius: 2 },
            ],
          }} options={{
            interaction: { mode: 'index', intersect: false },
            scales: { y: { ...ejeNum(), ticks: { callback: (v: number) => '$' + n0(v) } }, x: { ...sinGrilla, ticks: { maxTicksLimit: 6 } } },
            plugins: { tooltip: { callbacks: { label: (t: any) => `${t.dataset.label}: ${money(t.raw)}` } } },
          }} />
          <div className="formula">Facturado <b>{money(g.lista)}</b> por litro − IVA y otros {money(g.lista - g.final)} = costo final <b>{money(g.final)}</b></div>
        </Panel>
        <Panel id="g-est" span={12} title="Costos varios y administración" note="Administración, gastos generales e impuestos sobre facturación. Se reparten entre los dominios según los km.">
          <div className="tbl">
            <table>
              <thead><tr><th>Concepto</th><th>Rubro</th><th className="n">Monto</th><th style={{ width: '30%' }} /><th className="n">$/km</th></tr></thead>
              <tbody>{E.map(([r, k, v]) => (
                <tr key={r + k}><td>{k}</td><td>{r}</td><td className="n">{money(v)}</td>
                  <td><span className="bar-inline" style={{ width: `${(v / emax) * 100}%`, background: `var(${r === 'Impuestos' ? '--s2' : '--s1'})` }} /></td>
                  <td className="n">{money(v / kmc)}</td></tr>
              ))}</tbody>
              <tfoot><tr><th colSpan={2}>Total estructura{d.share < 1 ? ' (parte de la selección)' : ''}</th><th className="n">{moneyM(etot)}</th><th /><th className="n">{money(etot / kmc)}</th></tr></tfoot>
            </table>
          </div>
        </Panel>
      </section>
    </>
  );
}

