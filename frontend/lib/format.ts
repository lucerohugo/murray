// Todos los números completos, sin abreviar (nada de "2,4 M" o "20k"), con separador de miles y coma decimal.
const nf0 = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
const nf1 = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Cantidades y km: enteros sin decimales, y con hasta 2 decimales si los tienen. */
export const n0 = (v: number) => nf0.format(v);
export const n1 = (v: number) => nf1.format(v);
export const n2 = (v: number) => nf2.format(v);
/** Pesos con 2 decimales: $ 1.234.567,89 */
export const money = (v: number) => `${v < 0 ? '−' : ''}$ ${nf2.format(Math.abs(v))}`;
/** Antes abreviaba en millones; ahora muestra el monto completo. */
export const moneyM = money;
export const pct = (v: number) => (isFinite(v) ? `${nf2.format(v * 100)} %` : '–');
export const short = (s: string, n = 22) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
/** Ejes de los gráficos: monto completo (las marcas del eje son números redondos, sin centavos). */
export const axisMoney = (v: number | string) => {
  const x = Number(v);
  return `${x < 0 ? '−' : ''}$ ${nf0.format(Math.abs(x))}`;
};
