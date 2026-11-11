'use client';
import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useDatos } from '@/components/Providers';
import { ChartBox, barra, css, ejeMoney, sinGrilla } from '@/components/ChartBox';
import { Delta, Kpis, Legend, Panel, Split, ViewHead } from '@/components/ui';
import { GRUPOS, GRUPO_COLOR } from '@/lib/engine';
import { money, moneyM, n0, n1, pct } from '@/lib/format';

export default function Facturacion() {
  const { eng, F, prev, theme, setSelUnit } = useDatos();
  const router = useRouter();
  const [pa, pb] = prev;

  const d = useMemo(() => {
    const c = eng.calc(F.desde, F.hasta, F), p = eng.calc(pa, pb, F);
    const cart = eng.cartera(F.hasta, F), calle = cart.reduce((s, x) => s + x.total, 0);
    const callep = eng.cartera(pb, F).reduce((s, x) => s + x.total, 0);
    const B = eng.buckets(F.desde, F.hasta), S = B.map(x => eng.calc(x.a, x.b, F));
    const us = c.units.filter(x => !x.parada).sort((a, b) => b.neto - a.neto);
    const grupos = GRUPOS.map(([n, rs]) => [n, rs.reduce((s, r) => s + (c.rub[r] ?? 0), 0)] as [string, number]);
    // alertas
    const al: [string, string, string, string][] = [];
    const avgL = c.litros / (c.units.reduce((s, x) => s + x.km, 0) || 1);
    us.filter(x => x.neto < 0).forEach(x => al.push(['bad', '✕', `${x.u.id} pierde ${moneyM(-x.neto)}`, `Cuesta ${money(x.costoKm)}/km y factura ${money(x.factKm)}/km.`]));
    const par = c.units.filter(x => x.parada && x.total > 0);
    if (par.length) al.push(['warn', '!', `${par.length} unidad${par.length > 1 ? 'es' : ''} sin viajes`, `${par.map(x => x.u.id).join(', ')}. Costo sin producir: ${moneyM(par.reduce((s, x) => s + x.total, 0))}.`]);
    const deu: Record<string, number> = {};
    cart.filter(x => x.atraso > 60).forEach(x => (deu[x.cliente] = (deu[x.cliente] ?? 0) + x.total));
    Object.entries(deu).sort((a, b) => b[1] - a[1]).slice(0, 2).forEach(([k, v]) => al.push(['bad', '$', `${k} debe ${moneyM(v)} con más de 60 días`, 'Revisar antes de aceptar viajes nuevos.']));
    us.filter(x => x.km > 2000 && x.litros / x.km > avgL * 1.15).slice(0, 2)
      .forEach(x => al.push(['warn', 'L', `${x.u.id} consume ${n1((x.litros / x.km) * 100)} L/100 km`, `El promedio general es ${n1(avgL * 100)}.`]));
    if (c.fact && c.res / c.fact < 0.1) al.push(['warn', '%', `Margen bajo: ${pct(c.res / c.fact)}`, 'Por debajo del 10% en el período.']);
    if (!al.length) al.push(['ok', '✓', 'Nada fuera de lo normal', 'Todos los dominios dan resultado positivo.']);
    return { c, p, calle, callep, B, S, us, grupos, al: al.slice(0, 6) };
  }, [eng, F, pa, pb]);
  const { c, p, B, S, us, grupos } = d;

  return (
    <>
      <ViewHead slug="facturacion" />
      <Kpis items={[
        ['Facturación neta', moneyM(c.fact), <Delta a={c.fact} b={p.fact} />, true],
        ['Costo total', moneyM(c.costo), <Delta a={c.costo} b={p.costo} inv />],
        ['Resultado', <span className={c.res < 0 ? 'down' : 'up'}>{moneyM(c.res)}</span>, `Margen ${pct(c.res / c.fact)}`],
        ['Viajes', n0(c.trips.length), <Delta a={c.trips.length} b={p.trips.length} />],
        ['Km recorridos', n0(c.km), `${money(c.costo / (c.kmCost || 1))} de costo por km`],
        ['Plata en la calle', moneyM(d.calle), <Delta a={d.calle} b={d.callep} inv />],
      ]} />
      <section className="grid">
        <Panel id="r-evol" span={8} title="Ingresos contra costos" note="Facturación neta (flete − descuento, sin IVA) y costo total devengado en cada tramo del período.">
          <Legend items={[['Facturación neta', '--s1'], ['Costo total', '--s2']]} />
          <ChartBox label="Ingresos contra costos" type="line" key={theme} data={{
            labels: B.map(x => x.l), datasets: [
              { label: 'Facturación', data: S.map(s => s.fact), borderColor: css('--s1'), backgroundColor: css('--s1'), borderWidth: 2, pointRadius: B.length > 40 ? 0 : 3, tension: 0.25 },
              { label: 'Costo', data: S.map(s => s.costo), borderColor: css('--s2'), backgroundColor: css('--s2'), borderWidth: 2, pointRadius: B.length > 40 ? 0 : 3, tension: 0.25 },
            ],
          }} options={{
            interaction: { mode: 'index', intersect: false },
            scales: { y: { ...ejeMoney(), beginAtZero: true }, x: { ...sinGrilla, ticks: { maxTicksLimit: 12 } } },
            plugins: { tooltip: { callbacks: {
              label: (x: any) => `${x.dataset.label}: ${moneyM(x.raw)}`,
              footer: (i: any[]) => `Resultado: ${moneyM(i[0].raw - i[1].raw)} · ${S[i[0].dataIndex].trips.length} viajes`,
            } } },
          }} />
        </Panel>
        <Panel id="r-alerts" span={4} title="Alertas" note="Lo que se sale de lo normal en este período.">
          <ul className="alerts">
            {d.al.map(([k, i, t, s]) => (
              <li key={t}><span className={`ico ${k}`} aria-hidden="true">{i}</span><div><b>{t}</b><span className="t">{s}</span></div></li>
            ))}
          </ul>
        </Panel>
        <Panel id="r-units" title="Neto por dominio" note="Ingreso menos costo de cada camión, con su parte de la estructura según los km. Tocá una barra para ver el dominio.">
          <Legend items={[['Gana', '--good'], ['Pierde', '--bad']]} />
          <ChartBox label="Neto por dominio" type="bar" height={400} data={{
            labels: us.map(x => x.u.id),
            datasets: [{ data: us.map(x => x.neto), backgroundColor: us.map(x => (x.neto < 0 ? css('--bad') : css('--good'))), ...barra({ borderSkipped: false, maxBarThickness: 16 }) }],
          }} options={{
            indexAxis: 'y',
            scales: { x: ejeMoney(), y: { ...sinGrilla, ticks: { font: { family: css('--f-mono'), size: 11 } } } },
            plugins: { tooltip: { callbacks: { label: (x: any) => `Resultado ${moneyM(x.raw)} · margen ${pct(x.raw / us[x.dataIndex].fact)}` } } },
            onClick: (_e: unknown, el: { index: number }[]) => { if (el[0]) { setSelUnit(us[el[0].index].u.id); router.push('/dominios'); } },
          }} />
        </Panel>
        <Panel id="r-grupos" title="En qué se va la plata" note="Costo del período agrupado en cinco grandes bloques.">
          <ChartBox label="Costo por bloque" type="bar" height={250} data={{
            labels: grupos.map(x => x[0]),
            datasets: [{ data: grupos.map(x => x[1]), backgroundColor: GRUPO_COLOR.map(css), ...barra() }],
          }} options={{
            indexAxis: 'y', scales: { x: ejeMoney(), y: sinGrilla },
            plugins: { tooltip: { callbacks: { label: (x: any) => `${moneyM(x.raw)} · ${pct(x.raw / c.costo)}` } } },
          }} />
          <Split variable={c.variable / c.costo} />
        </Panel>
      </section>
    </>
  );
}
