'use client';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { Dataset, Filtros } from '@/lib/types';
import { cargarDataset } from '@/lib/api';
import { createEngine, type Engine } from '@/lib/engine';

export const PRESETS: [string, string][] = [['mes', 'Este mes'], ['ant', 'Mes anterior'], ['30', '30 días'], ['90', '90 días'], ['anio', '12 meses']];
export const DIMENSIONES = ['empresa', 'servicio', 'unidad', 'chofer', 'cliente'] as const;
export type Dimension = (typeof DIMENSIONES)[number];

interface Ctx {
  ds: Dataset | null;
  eng: Engine | null;
  error: string | null;
  F: Filtros;
  setF: (patch: Partial<Filtros>) => void;
  preset: (k: string) => void;
  limpiar: () => void;
  prev: [number, number];
  selUnit: string | null;
  setSelUnit: (u: string | null) => void;
  theme: number; // cambia cuando cambia el tema claro/oscuro, para redibujar los gráficos
}
const TableroCtx = createContext<Ctx | null>(null);

const VACIO: Filtros = { desde: 0, hasta: 0, preset: 'mes', empresa: '', servicio: '', unidad: '', chofer: '', cliente: '' };

function rangoPreset(ds: Dataset, k: string): [number, number] {
  const mi = ds.meses.length - 1, hoy = ds.hoy;
  if (k === 'mes') return [ds.meses[mi].start, hoy];
  if (k === 'ant') return mi > 0 ? [ds.meses[mi - 1].start, ds.meses[mi - 1].end] : [ds.meses[mi].start, hoy];
  if (k === '30') return [Math.max(ds.inicio, hoy - 29), hoy];
  if (k === '90') return [Math.max(ds.inicio, hoy - 89), hoy];
  return [ds.inicio, hoy];
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [ds, setDs] = useState<Dataset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [F, setFState] = useState<Filtros>(VACIO);
  const [selUnit, setSelUnit] = useState<string | null>(null);
  const [theme, setTheme] = useState(0);

  useEffect(() => {
    cargarDataset()
      .then(d => { setDs(d); const [a, b] = rangoPreset(d, 'mes'); setFState(f => ({ ...f, desde: a, hasta: b, preset: 'mes' })); })
      .catch(e => setError(e instanceof Error ? e.message : String(e)));
    const mq = matchMedia('(prefers-color-scheme: dark)');
    const bump = () => setTheme(t => t + 1);
    mq.addEventListener('change', bump);
    const mo = new MutationObserver(bump);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => { mq.removeEventListener('change', bump); mo.disconnect(); };
  }, []);

  const eng = useMemo(() => (ds ? createEngine(ds) : null), [ds]);
  const setF = useCallback((patch: Partial<Filtros>) => setFState(f => ({ ...f, ...patch })), []);
  const preset = useCallback((k: string) => { if (!ds) return; const [a, b] = rangoPreset(ds, k); setFState(f => ({ ...f, desde: a, hasta: b, preset: k })); }, [ds]);
  const limpiar = useCallback(() => { if (!ds) return; const [a, b] = rangoPreset(ds, 'mes'); setFState({ ...VACIO, desde: a, hasta: b }); }, [ds]);
  const n = F.hasta - F.desde + 1;
  const prev: [number, number] = [F.desde - n, F.desde - 1];

  return (
    <TableroCtx.Provider value={{ ds, eng, error, F, setF, preset, limpiar, prev, selUnit, setSelUnit, theme }}>
      {children}
    </TableroCtx.Provider>
  );
}

export function useTablero() {
  const c = useContext(TableroCtx);
  if (!c) throw new Error('useTablero fuera de Providers');
  return c;
}

/** Para las vistas: garantiza que los datos ya están cargados. */
export function useDatos() {
  const c = useTablero();
  if (!c.ds || !c.eng) throw new Error('Datos no cargados');
  return { ...c, ds: c.ds, eng: c.eng };
}
