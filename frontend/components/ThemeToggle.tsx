'use client';
import { useEffect, useState } from 'react';

/** Botón claro / oscuro. Guarda la elección en el navegador; sin elección sigue al sistema. */
export function ThemeToggle() {
  const [oscuro, setOscuro] = useState(false);

  useEffect(() => {
    const t = document.documentElement.dataset.theme;
    setOscuro(t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches);
  }, []);

  const cambiar = () => {
    const nuevo = oscuro ? 'light' : 'dark';
    document.documentElement.dataset.theme = nuevo;
    try { localStorage.setItem('tema', nuevo); } catch {}
    setOscuro(!oscuro);
  };

  return (
    <button type="button" className="btn theme-btn" onClick={cambiar} aria-label={oscuro ? 'Pasar a modo claro' : 'Pasar a modo oscuro'} title={oscuro ? 'Modo claro' : 'Modo oscuro'}>
      {oscuro ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      )}
      <span>{oscuro ? 'Claro' : 'Oscuro'}</span>
    </button>
  );
}
