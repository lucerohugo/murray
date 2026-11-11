'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { VISTAS } from '@/lib/origen';

export function Header() {
  const path = usePathname();
  return (
    <header>
      <div className="wrap">
        <div className="hrow">
          <div className="brand">
            <svg width="40" height="28" viewBox="0 0 40 28" aria-hidden="true">
              <rect x="1" y="5" width="24" height="15" rx="2" fill="var(--s1)" />
              <path d="M25 9h7l5 6v5H25z" fill="var(--ink)" />
              <rect x="28" y="10.5" width="4" height="4" rx=".5" fill="var(--panel)" />
              <circle cx="8" cy="22" r="3.5" fill="var(--ink)" stroke="var(--panel)" strokeWidth="1.5" />
              <circle cx="31" cy="22" r="3.5" fill="var(--ink)" stroke="var(--panel)" strokeWidth="1.5" />
            </svg>
            <div><h1>TABLERO MURRAY</h1><small>Gestión de transporte</small></div>
          </div>
        </div>
        <nav className="tabs" aria-label="Áreas">
          {VISTAS.map(v => (
            <Link key={v.slug} href={`/${v.slug}`} aria-current={path === `/${v.slug}` ? 'page' : undefined}>{v.nombre}</Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
