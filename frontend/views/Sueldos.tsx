'use client';
import { useMemo } from 'react';
import { useDatos } from '@/components/Providers';
import { ChartBox, barra, css, ejeMoney, segmento, sinGrilla } from '@/components/ChartBox';
import { Delta, Kpis, Legend, Panel, Plate, ViewHead } from '@/components/ui';
import { unitOk } from '@/lib/engine';
import { money, moneyM, n0, pct } from '@/lib/format';

export default function Sueldos() {
  const { ds, eng, F, prev } = useDatos();
  const [pa, pb] = prev;

  const d = useMemo(() => {
    const c = eng.calc(F.desde, F.hasta, F), p = eng.calc(pa, pb, F);
    const ch = c.units.map(x => {
      const ts = c.trips.filter(t => t.chofer === x.u.chofer);
      const fi = x.r['Choferes (fijo)'] ?? 0, va = x.r['Choferes (por km)'] ?? 0;
      return { d: x.u.chofer, u: x.u.id, n: ts.length, km: x.km, fact: ts.reduce((s, t) => s + t.neto, 0), fi, va, tot: fi + va };
    }).sort((a, b) => b.fact - a.fact);
    const tot = ch.reduce((s, o) => s + o.tot, 0), fi = ch.reduce((s, o) => s + o.fi, 0), fact = ch.reduce((s, o) => s + o.fact, 0), km = ch.reduce((s, o) => s + o.km, 0);
    const totp = p.units.reduce((s, x) => s + (x.r['Choferes (fijo)'] ?? 0) + (x.r['Choferes (por km)'] ?? 0), 0);
    const adm = c.C.est['Administración'] ?? 0;
    const mi = Math.max(0, eng.monthIdx(F.hasta)), Ms = ds.meses.slice(0, mi + 1), uok = unitOk(F);
    const S = Ms.map(M => {
      const C = eng.costs(M.start, Math.min(M.end, ds.hoy)); let a = 0, b = 0;
      Object.values(C.U).forEach(x => { if (uok(x.u)) { a += x.r['Choferes (fijo)'] ?? 0; b += x.r['Choferes (por km)'] ?? 0; } });
      return [a, b, C.est['Administración'] ?? 0];
    });
    return { ch, tot, fi, fact, km, totp, adm, Ms, S };
  }, [ds, eng, F, pa, pb]);
  const { ch } = d;
  const fmax = Math.max(1, ...ch.map(o => o.fact));
  const cs = ch.filter(o => o.n);

  return (
    <>
      <ViewHead slug="sueldos" />
      <Kpis items={[
        ['Costo de choferes', moneyM(d.tot), <Delta a={d.tot} b={d.totp} inv />, true],
        ['Choferes con viajes', `${cs.length} / ${ch.length}`],
        ['Parte fija', pct(d.fi / d.tot), 'El resto se paga por km'],
        ['Sueldo por km', `${money(d.tot / (d.km || 1))}`, 'Sobre km recorridos'],
        ['Administración', moneyM(d.adm), 'Sueldos no operativos'],
      ]} />
      <section className="grid">
        <Panel id="p-tbl" span={12} title="Sueldos x km" note="Sueldo dividido en parte fija (básico, antigüedad, extras, bono) y parte por km.">
          <div className="tbl">
            <table>
              <thead><tr><th>Chofer</th><th>Dominio</th><th className="n">Viajes</th><th className="n">Km</th><th className="n">Facturado</th><th style={{ width: '16%' }} /><th className="n">Fijo</th><th className="n">Por km</th><th className="n">Total</th><th className="n">$/km</th></tr></thead>
              <tbody>{ch.map(o => {
                return (
                  <tr key={o.d}><td>{o.d}</td><td><Plate p={o.u} /></td><td className="n">{o.n}</td><td className="n">{n0(o.km)}</td><td className="n">{moneyM(o.fact)}</td>
                    <td><span className="bar-inline" style={{ width: `${(o.fact / fmax) * 100}%` }} /></td>
                    <td className="n">{moneyM(o.fi)}</td><td className="n">{moneyM(o.va)}</td><td className="n">{moneyM(o.tot)}</td><td className="n">{o.km ? `${money(o.tot / o.km)}` : '–'}</td></tr>
                );
              })}</tbody>
            </table>
          </div>
        </Panel>
        <Panel id="p-bar" title="Facturado contra sueldo" note="Por chofer, en el período.">
          <Legend items={[['Facturado', '--s1'], ['Sueldo', '--s2']]} />
          <ChartBox label="Facturado contra sueldo" type="bar" height={400} data={{
            labels: cs.map(o => o.d.split(',')[0]), datasets: [
              { label: 'Facturado', data: cs.map(o => o.fact), backgroundColor: css('--s1'), ...barra({ maxBarThickness: 12 }) },
              { label: 'Sueldo', data: cs.map(o => o.tot), backgroundColor: css('--s2'), ...barra({ maxBarThickness: 12 }) },
            ],
          }} options={{
            indexAxis: 'y', scales: { x: ejeMoney(), y: sinGrilla },
            plugins: { tooltip: { callbacks: { title: (i: any[]) => cs[i[0].dataIndex].d, label: (t: any) => `${t.dataset.label}: ${moneyM(t.raw)}` } } },
          }} />
        </Panel>
        <Panel id="p-evol" title="Costo de personal por mes" note="Choferes (fijo y por km) y administración.">
          <Legend items={[['Choferes fijo', '--s1'], ['Choferes por km', '--s2'], ['Administración', '--s3']]} />
          <ChartBox label="Costo de personal por mes" type="bar" height={400} data={{
            labels: d.Ms.map(M => M.label),
            datasets: (['--s1', '--s2', '--s3'] as const).map((k, i) => ({ label: ['Choferes fijo', 'Choferes por km', 'Administración'][i], data: d.S.map(s => s[i]), ...segmento(css(k)) })),
          }} options={{
            scales: { x: { ...sinGrilla, stacked: true }, y: { ...ejeMoney(), stacked: true } },
            plugins: { tooltip: { mode: 'index', intersect: false, callbacks: { label: (t: any) => `${t.dataset.label}: ${moneyM(t.raw)}` } } },
          }} />
        </Panel>
      </section>
    </>
  );
}
