import type { Mes } from './types';

const DAY = 864e5;
export const MN = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** 'YYYY-MM-DD' → número de día (UTC) */
export const dn = (s: string) => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) / DAY;
export const dd = (n: number) => new Date(n * DAY);
export const iso = (n: number) => dd(n).toISOString().slice(0, 10);

export function buildMonths(from: number, to: number): Mes[] {
  const out: Mes[] = [];
  let y = dd(from).getUTCFullYear(), m = dd(from).getUTCMonth();
  for (;;) {
    const start = Date.UTC(y, m, 1) / DAY;
    if (start > to) break;
    const end = Date.UTC(y, m + 1, 1) / DAY - 1;
    out.push({ y, m, start, end, days: end - start + 1, key: `${y}-${String(m + 1).padStart(2, '0')}`, label: `${MN[m]} ${String(y).slice(2)}` });
    if (++m > 11) { m = 0; y++; }
  }
  return out;
}

export const fd = (n: number) => {
  const x = dd(n);
  return `${String(x.getUTCDate()).padStart(2, '0')}/${String(x.getUTCMonth() + 1).padStart(2, '0')}/${String(x.getUTCFullYear()).slice(2)}`;
};
export const fdl = (n: number) => { const x = dd(n); return `${x.getUTCDate()} ${MN[x.getUTCMonth()]} ${x.getUTCFullYear()}`; };
