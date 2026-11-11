'use client';
import { Chart as ChartJS, registerables, type ChartData, type ChartOptions, type ChartType } from 'chart.js';
import { Chart } from 'react-chartjs-2';
import { axisMoney } from '@/lib/format';
import { useTablero } from './Providers';

ChartJS.register(...registerables);

/** Lee un token de color de la hoja de estilos (cambia con el tema). */
export const css = (k: string) => (typeof window === 'undefined' ? '#888' : getComputedStyle(document.documentElement).getPropertyValue(k).trim());
export const col = (k: string) => (k.startsWith('--') ? css(k) : k);

function aplicarTema() {
  const D = ChartJS.defaults;
  D.color = css('--ink-2');
  D.borderColor = css('--line');
  D.font.family = css('--f-body');
  D.font.size = 12;
  D.maintainAspectRatio = false;
  if (D.animation) D.animation.duration = 250;
  D.plugins.legend.display = false;
  const T = D.plugins.tooltip;
  T.backgroundColor = css('--ink'); T.titleColor = css('--bg'); T.bodyColor = css('--bg'); T.footerColor = css('--bg');
  T.padding = 10; T.cornerRadius = 6; T.boxPadding = 4;
}

/* eslint-disable @typescript-eslint/no-explicit-any */
export function ChartBox({ type, data, options, height = 280, label }: {
  type: ChartType; data: ChartData<any, any, any> | any; options?: ChartOptions<any> | any; height?: number; label: string;
}) {
  const { theme } = useTablero();
  aplicarTema();
  return (
    <div className="chart" style={{ height }}>
      <Chart key={theme} type={type} data={data} options={options} aria-label={label} role="img" />
    </div>
  );
}

/* ---------- piezas comunes de los gráficos ---------- */
export const ejeMoney = () => ({ ticks: { callback: (v: number | string) => axisMoney(v) }, grid: { color: css('--line') }, border: { display: false } });
export const ejeNum = () => ({ grid: { color: css('--line') }, border: { display: false } });
export const sinGrilla = { grid: { display: false }, border: { display: false } };
export const barra = (o: Record<string, unknown> = {}) => ({ borderRadius: 4, borderSkipped: 'start' as const, maxBarThickness: 22, borderWidth: 0, ...o });
export const segmento = (c: string) => ({
  backgroundColor: c, borderColor: css('--panel'), borderWidth: { top: 2, right: 2 }, borderSkipped: false as const, borderRadius: 0, maxBarThickness: 28,
});
