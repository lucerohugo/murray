'use client';
import { useMemo } from 'react';
import { useDatos } from '@/components/Providers';
import { ChartBox, barra, css, ejeNum, segmento, sinGrilla } from '@/components/ChartBox';
import { Delta, Empty, Kpis, Legend, Panel, Pill, Plate, ViewHead } from '@/components/ui';
import { GRUPOS, GRUPO_COLOR, RUBROS, sumM, unitOk, type Montos } from '@/lib/engine';
import { fd } from '@/lib/dates';
import { money, moneyM, n0, n1, pct } from '@/lib/format';

export default function Dominios() {
  const { ds, eng, F, prev, selUnit, setSelUnit } = useDatos();
  const [pa, pb] = prev;

  const d = useMemo(() => {
    const c = eng.calc(F.desde, F.hasta, F), p = eng.calc(pa, pb, F), U = c.units, act = U.filter(x => !x.parada);
    const km = U.reduce((s, x) => s + x.km, 0), kmp = p.units.reduce((s, x) => s + x.km, 0);
    const mant = U.reduce((s, x) => s + (x.r['Mantenimiento'] ?? 0), 0), mantp = p.units.reduce((s, x) => s + (x.r['Mantenimiento'] ?? 0), 0);
    const idle = U.filter(x => x.parada).reduce((s, x) => s + x.total, 0);
    const ck = U.reduce((s, x) => s + (x.km ? x.total : 0), 0) / (km || 1), ckp = p.units.reduce((s, x) => s + (x.km ? x.total : 0), 0) / (kmp || 1);
    const rows = [...U].sort((a, b) => b.neto - a.neto);
    const fl: Montos = {}; const fkm = act.reduce((s, y) => s + y.km, 0);
    act.forEach(y => Object.entries(y.all).forEach(([r, v]) => (fl[r] = (fl[r] ?? 0) + (v ?? 0))));
    const avg = (c.litros / (km || 1)) * 100;
    const cb = act.filter(y => y.km > 300).sort((a, b) => b.litros / b.km - a.litros / a.km);
    const uok = unitOk(F);
    const ev = ds.gastosDia.filter(g => g.rubro === 'Mantenimiento' && g.fecha >= F.desde && g.fecha <= F.hasta && g.unidad && uok(ds.unidades.find(u => u.id === g.unidad)!))
      .sort((a, b) => b.fecha - a.fecha);
    return { c, U, act, km, kmp, mant, mantp, idle, ck, ckp, rows, fl, fkm, avg, cb, ev };
  }, [ds, eng, F, pa, pb]);
  const { c, U, act, rows, fl, fkm, cb, ev } = d;

  const sel = selUnit && act.find(x => x.u.id === selUnit) ? selUnit : act[0]?.u.id ?? null;
  const x = sel ? c.C.U[sel] : null;
  // Al elegir un dominio: baja hasta su detalle y lo resalta un momento.
  const elegir = (id: string) => {
    setSelUnit(id);
    requestAnimationFrame(() => {
      document.getElementById('f-desg')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      ['f-desg', 'f-trend'].forEach(k => {
        const el = document.getElementById(k);
        if (!el) return;
        el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
      });
    });
  };
  const gv = (o: Montos, k: number) => GRUPOS.map(([, rs]) => rs.reduce((s, r) => s + (o[r] ?? 0), 0) / (k || 1));

  const trend = useMemo(() => {
    const mi = Math.max(0, eng.monthIdx(F.hasta)), Ms = ds.meses.slice(0, mi + 1);
    return { Ms, tr: Ms.map(M => {
      const C = eng.costs(M.start, Math.min(M.end, ds.hoy)), y = sel ? C.U[sel] : null, a = Object.values(C.U).filter(z => z.km);
      return [y && y.km ? y.costoKm : null, a.reduce((s, z) => s + z.total, 0) / (a.reduce((s, z) => s + z.km, 0) || 1)] as [number | null, number];
    }) };
  }, [ds, eng, F.hasta, sel]);

  return (
    <>
      <ViewHead slug="dominios" />
      <Kpis items={[
        ['Unidades activas', `${act.length} / ${U.length}`, `${U.length - act.length} sin viajes en el período`, true],
        ['Km recorridos', n0(d.km), <Delta a={d.km} b={d.kmp} />],
        ['Costo por km', `${money(d.ck)}`, <Delta a={d.ck} b={d.ckp} inv />],
        ['Consumo promedio', `${n1(d.avg)} L`, `cada 100 km · ${n0(c.litros)} L`],
        ['Reparaciones', moneyM(d.mant), <Delta a={d.mant} b={d.mantp} inv />],
        ['Costo de unidades paradas', moneyM(d.idle), 'Seguro, patente, chofer y amortización'],
      ]} />
      <section className="grid">
        <Panel id="f-units" span={12} title="Dominios" note="Tocá una fila: la página baja al detalle de costos de ese camión.">
          <div className="tbl">
            <table>
              <thead><tr><th>Dominio</th><th>Servicio</th><th>Chofer</th><th className="n">Viajes</th><th className="n">Km</th><th className="n">% vacío</th><th className="n">L/100 km</th><th className="n">Ingreso/km</th><th className="n">Costo/km</th><th className="n">Resultado</th><th>Estado</th></tr></thead>
              <tbody>{rows.map(y => y.parada ? (
                <tr key={y.u.id}><td><Plate p={y.u.id} /></td><td>{y.u.servicio}</td><td>{y.u.chofer}</td><td className="n">0</td><td className="n">0</td><td className="n">–</td><td className="n">–</td><td className="n">–</td><td className="n">–</td><td className="n">{moneyM(-y.total)}</td><td><Pill>Parada</Pill></td></tr>
              ) : (
                <tr key={y.u.id} className={`click ${y.u.id === sel ? 'sel' : ''}`} tabIndex={0} onClick={() => elegir(y.u.id)}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); elegir(y.u.id); } }}>
                  <td><Plate p={y.u.id} /></td><td>{y.u.servicio}</td><td>{y.u.chofer}</td><td className="n">{y.viajes}</td><td className="n">{n0(y.km)}</td>
                  <td className="n">{pct((y.km - y.kmc) / y.km)}</td><td className="n">{n1((y.litros / y.km) * 100)}</td><td className="n">{money(y.factKm)}</td><td className="n">{money(y.costoKm)}</td><td className="n">{moneyM(y.neto)}</td>
                  <td>{y.neto < 0 ? <Pill k="bad">✕ Pierde</Pill> : y.neto / y.fact < 0.15 ? <Pill k="warn">! Margen bajo</Pill> : <Pill k="ok">✓ Bien</Pill>}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Panel>
        <Panel id="f-desg" span={7} title={<>Costo por km del dominio {sel && <Plate p={sel} />}</>} note={sel ? `Detalle del dominio ${sel} contra el promedio de todos los dominios. Para ver otro, elegilo en la tabla de arriba.` : 'El dominio elegido contra el promedio de todos los dominios.'}>
          <Legend items={GRUPOS.map(([n], i) => [n, GRUPO_COLOR[i]] as [string, string])} />
          {x && x.km ? <>
            <ChartBox label="Desglose del costo por km" type="bar" height={180} data={{
              labels: [sel, 'Promedio general'],
              datasets: GRUPOS.map(([n], i) => ({ label: n, data: [gv(x.all, x.km)[i], gv(fl, fkm)[i]], ...segmento(css(GRUPO_COLOR[i])), borderWidth: { right: 2 } })),
            }} options={{
              indexAxis: 'y',
              scales: { x: { ...ejeNum(), stacked: true, ticks: { callback: (v: number) => '$' + n0(v) } }, y: { ...sinGrilla, stacked: true } },
              plugins: { tooltip: { callbacks: { label: (t: any) => `${t.dataset.label}: ${money(t.raw)}/km` } } },
            }} />
            <div className="tbl" style={{ marginTop: 8 }}>
              <table>
                <thead><tr><th>Rubro</th><th className="n">Dominio $/km</th><th className="n">Promedio $/km</th><th className="n">Diferencia</th></tr></thead>
                <tbody>{RUBROS.map(r => {
                  const u = (x.all[r] ?? 0) / x.km, f = (fl[r] ?? 0) / (fkm || 1), df = u - f;
                  return <tr key={r}><td>{r}</td><td className="n">{money(u)}</td><td className="n">{money(f)}</td><td className={`n ${df > f * 0.15 && df > 3 ? 'down' : ''}`}>{df > 0 ? '+' : ''}{n1(df)}</td></tr>;
                })}</tbody>
                <tfoot><tr><th>Total</th><th className="n">{money(x.costoKm)}</th><th className="n">{money(sumM(fl) / (fkm || 1))}</th><th /></tr></tfoot>
              </table>
            </div>
          </> : <p className="empty">Ningún dominio tuvo viajes con estos filtros.</p>}
        </Panel>
        <Panel id="f-trend" span={5} title={<>Costo por km mes a mes {sel && <Plate p={sel} />}</>} note="Últimos 12 meses hasta la fecha elegida.">
          <Legend items={[[sel ?? 'Dominio elegido', '--s1'], ['Promedio general', '--ink-3']]} />
          <ChartBox label="Costo por km mes a mes" type="line" data={{
            labels: trend.Ms.map(M => M.label), datasets: [
              { label: sel ?? '', data: trend.tr.map(t => t[0]), borderColor: css('--s1'), backgroundColor: css('--s1'), borderWidth: 2, pointRadius: 3, spanGaps: false },
              { label: 'Promedio general', data: trend.tr.map(t => t[1]), borderColor: css('--ink-3'), backgroundColor: css('--ink-3'), borderWidth: 2, borderDash: [4, 4], pointRadius: 0 },
            ],
          }} options={{
            interaction: { mode: 'index', intersect: false },
            scales: { y: { ...ejeNum(), ticks: { callback: (v: number) => '$' + n0(v) } }, x: sinGrilla },
            plugins: { tooltip: { callbacks: { label: (t: any) => (t.raw == null ? `${t.dataset.label}: parada` : `${t.dataset.label}: ${money(t.raw)}/km`) } } },
          }} />
        </Panel>
        <Panel id="f-comb" title="Consumo de gasoil" note="Litros cada 100 km recorridos.">
          <ChartBox label="Consumo de gasoil" type="bar" data={{
            labels: cb.map(y => y.u.id),
            datasets: [{ data: cb.map(y => (y.litros / y.km) * 100), backgroundColor: cb.map(y => ((y.litros / y.km) * 100 > d.avg * 1.15 ? css('--s2') : css('--s3'))), ...barra() }],
          }} options={{
            scales: { y: { ...ejeNum(), ticks: { callback: (v: number) => v + ' L' } }, x: { ...sinGrilla, ticks: { font: { family: css('--f-mono'), size: 10 }, maxRotation: 60, minRotation: 45 } } },
            plugins: { tooltip: { callbacks: {
              label: (t: any) => `${n1(t.raw)} L/100 km · ${n0(cb[t.dataIndex].litros)} L`,
              footer: () => `Promedio general ${n1(d.avg)} L/100 km`,
            } } },
          }} />
        </Panel>
        <Panel id="f-mant" title="Reparaciones del período" note="Mantenimiento correctivo cargado con fecha.">
          <div className="tbl" style={{ maxHeight: 290 }}>
            <table>
              {ev.length ? <>
                <thead><tr><th>Fecha</th><th>Dominio</th><th>Trabajo</th><th className="n">Monto</th></tr></thead>
                <tbody>{ev.map((g, i) => <tr key={i}><td>{fd(g.fecha)}</td><td><Plate p={g.unidad!} /></td><td>{g.concepto}</td><td className="n">{money(g.monto)}</td></tr>)}</tbody>
                <tfoot><tr><th colSpan={3}>{ev.length} reparaciones</th><th className="n">{moneyM(ev.reduce((s, g) => s + g.monto, 0))}</th></tr></tfoot>
              </> : <Empty>Sin reparaciones en el período.</Empty>}
            </table>
          </div>
        </Panel>
      </section>
    </>
  );
}
