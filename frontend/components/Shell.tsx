'use client';
import { useTablero } from './Providers';
import { Header } from './Header';
import { FilterBar } from './FilterBar';

export function Shell({ children }: { children: React.ReactNode }) {
  const { ds, error } = useTablero();
  return (
    <>
      <Header />
      {ds && <FilterBar />}
      <main className="wrap">
        {error ? (
          <div className="loading"><p className="err">No se pudieron cargar los datos. {error}</p></div>
        ) : ds ? children : (
          <div className="loading"><p>Cargando datos…</p></div>
        )}
      </main>
    </>
  );
}
