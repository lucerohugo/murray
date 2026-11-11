'use client';
import { dn, iso } from '@/lib/dates';
import { PRESETS, useDatos, type Dimension } from './Providers';

export function FilterBar() {
  const { ds, F, setF, preset, limpiar } = useDatos();
  const opciones: [Dimension, string, string, string[]][] = [
    ['empresa', 'Razón social', 'Todas', ds.empresas],
    ['servicio', 'Servicio', 'Todos', ds.servicios],
    ['unidad', 'Dominio', 'Todos', ds.unidades.map(u => u.id)],
    ['chofer', 'Chofer', 'Todos', Array.from(new Set(ds.unidades.map(u => u.chofer).filter(Boolean))).sort()],
    ['cliente', 'Cliente', 'Todos', ds.clientes],
  ];
  const cambiarFecha = (desde: string, hasta: string) => {
    if (!desde || !hasta) return;
    let a = dn(desde), b = dn(hasta);
    if (a > b) [a, b] = [b, a];
    setF({ desde: Math.max(ds.inicio, a), hasta: Math.min(ds.hoy, b), preset: '' });
  };
  return (
    <div className="filters">
      <div className="wrap frow">
        <div className="f">
          <label>Período</label>
          <div className="presets">
            {PRESETS.map(([k, n]) => (
              <button key={k} type="button" aria-pressed={F.preset === k} onClick={() => preset(k)}>{n}</button>
            ))}
          </div>
        </div>
        <div className="f"><label htmlFor="f-desde">Desde</label>
          <input type="date" id="f-desde" min={iso(ds.inicio)} max={iso(ds.hoy)} value={iso(F.desde)} onChange={e => cambiarFecha(e.target.value, iso(F.hasta))} /></div>
        <div className="f"><label htmlFor="f-hasta">Hasta</label>
          <input type="date" id="f-hasta" min={iso(ds.inicio)} max={iso(ds.hoy)} value={iso(F.hasta)} onChange={e => cambiarFecha(iso(F.desde), e.target.value)} /></div>
        <div className="divider" aria-hidden="true" />
        {opciones.map(([k, label, todos, ops]) => (
          <div className="f" key={k}>
            <label htmlFor={`f-${k}`}>{label}</label>
            <select id={`f-${k}`} value={F[k]} onChange={e => setF({ [k]: e.target.value })}>
              <option value="">{todos}</option>
              {ops.map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
        ))}
        <button className="btn ghost" type="button" onClick={limpiar}>Limpiar filtros</button>
      </div>
    </div>
  );
}
