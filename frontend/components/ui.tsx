'use client';
import type { ReactNode } from 'react';
import { VISTAS } from '@/lib/origen';
import { fdl } from '@/lib/dates';
import { n1 } from '@/lib/format';
import { DIMENSIONES, useDatos } from './Providers';

export const Plate = ({ p }: { p: string }) => <span className="plate"><span>{p}</span></span>;
export const Pill = ({ k, children }: { k?: 'ok' | 'bad' | 'warn' | ''; children: ReactNode }) => <span className={`pill ${k ?? ''}`}>{children}</span>;
export const Sw = ({ c }: { c: string }) => <i style={{ background: `var(${c})` }} />;

export function Legend({ items }: { items: [string, string][] }) {
  return <div className="legend">{items.map(([l, c]) => <span key={l}><Sw c={c} />{l}</span>)}</div>;
}

/** Variación contra el período anterior. inv = true cuando subir es malo (costos). */
export function Delta({ a, b, inv }: { a: number; b: number; inv?: boolean }) {
  if (!b || !isFinite(a / b)) return null;
  const d = (a - b) / Math.abs(b), good = inv ? d < 0 : d > 0;
  return <><span className={`delta ${good ? 'up' : 'down'}`}>{d > 0 ? '▲' : '▼'} {n1(Math.abs(d) * 100)}%</span> vs período ant.</>;
}

export type KpiItem = [label: string, value: ReactNode, sub?: ReactNode, hero?: boolean];
export function Kpis({ items }: { items: KpiItem[] }) {
  return (
    <div className="kpis">
      {items.map(([l, v, s, h]) => {
        return (
          <div key={l} className={`kpi ${h ? 'hero' : ''}`}>
            <div className="lbl">{l}</div>
            <div className="val">{v}</div>
            <div className="sub">{s ?? ' '}</div>
          </div>
        );
      })}
    </div>
  );
}

export function Split({ variable }: { variable: number }) {
  if (!isFinite(variable)) return null;
  return (
    <div className="split">
      <div style={{ flex: variable, background: 'var(--s2)' }}>Variable {n1(variable * 100)} %</div>
      <div style={{ flex: 1 - variable, background: 'var(--s1)' }}>Fijo {n1((1 - variable) * 100)} %</div>
    </div>
  );
}

/** Panel con título y nota. */
export function Panel({ id, span = 6, title, note, children }: { id: string; span?: 4 | 5 | 6 | 7 | 8 | 12; title: ReactNode; note?: ReactNode; children: ReactNode }) {
  return (
    <div className={`panel s${span}`} id={id}>
      <h3>{title}</h3>
      {note && <p className="note">{note}</p>}
      {children}
    </div>
  );
}

export const Src = ({ children }: { children: ReactNode }) => <span className="src">{children}</span>;
export const Empty = ({ children }: { children: ReactNode }) => <tbody><tr><td className="empty">{children}</td></tr></tbody>;

/** Encabezado de cada vista: título, rango y filtros activos. */
export function ViewHead({ slug }: { slug: (typeof VISTAS)[number]['slug'] }) {
  const { F, setF } = useDatos();
  const v = VISTAS.find(x => x.slug === slug)!;
  const activos = DIMENSIONES.filter(k => F[k]);
  return (
    <>
      <div className="vhead">
        <h2>{v.nombre}</h2>
        <p>{fdl(F.desde)} – {fdl(F.hasta)} · {F.hasta - F.desde + 1} días</p>
        <div className="chips">
          {activos.map(k => (
            <span className="chip" key={k}>{F[k]}<button type="button" aria-label={`Quitar filtro ${F[k]}`} onClick={() => setF({ [k]: '' })}>×</button></span>
          ))}
        </div>
      </div>
    </>
  );
}
