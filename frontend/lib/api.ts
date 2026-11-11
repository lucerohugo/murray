/* =====================================================================
   ACCESO A DATOS
   Pide GET {NEXT_PUBLIC_API_URL}/dataset al backend (frontend/.env.local).
   No hay datos de respaldo: todo lo que se muestra sale del backend.
   ===================================================================== */
import type { Dataset, RawDataset } from './types';
import { buildMonths, dn } from './dates';

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const API_KEY = process.env.NEXT_PUBLIC_API_KEY; // la API_SYNC_KEY del backend

export async function cargarDataset(): Promise<Dataset> {
  // ---- DATOS FIJOS PARA LA DEMO (Vercel sin backend) -------------------------------
  // Mientras USAR_DATOS_FIJOS sea true, el tablero usa lib/datos-planilla.json: una copia
  // exacta de GET /api/dataset con la PLANILLA COSTO MAYO, sin llamar al backend.
  // Para volver al backend: borrar este bloque y el archivo lib/datos-planilla.json.
  const USAR_DATOS_FIJOS = true;
  if (USAR_DATOS_FIJOS || !API_URL) {
    const fijo = (await import('./datos-planilla.json')).default as unknown as RawDataset;
    return normalizar(fijo);
  }
  // ---- FIN DATOS FIJOS ---------------------------------------------------------------
  let res: Response;
  try {
    res = await fetch(`${API_URL.replace(/\/$/, '')}/dataset`, {
      cache: 'no-store',
      headers: API_KEY ? { Authorization: `Bearer ${API_KEY}` } : undefined,
    });
  } catch {
    throw new Error(`No se pudo conectar con el backend en ${API_URL}. ¿Está corriendo "python manage.py runserver"?`);
  }
  if (!res.ok) throw new Error(`El backend respondió ${res.status} al pedir los datos.`);
  const raw: RawDataset = await res.json();
  if (!raw.viajes.length) throw new Error('El backend no tiene viajes cargados. Correr: python manage.py importar_excel');
  return normalizar(raw);
}

/** Convierte el JSON del contrato a la forma interna (fechas como número de día). */
export function normalizar(raw: RawDataset): Dataset {
  const hoy = dn(raw.fechaCorte);
  const fechas = raw.viajes.map(v => dn(v.fecha));
  const primera = fechas.length ? Math.min(...fechas) : hoy;
  const meses = buildMonths(primera, hoy);
  const mesIdx = new Map(meses.map((M, i) => [M.key, i]));
  return {
    fuente: raw.fuente,
    hoy,
    inicio: meses[0].start,
    meses,
    unidades: raw.unidades,
    clientes: raw.clientes.map(c => c.nombre).sort(),
    servicios: Array.from(new Set(raw.unidades.map(u => u.servicio))),
    empresas: Array.from(new Set(raw.viajes.map(v => v.empresa))).sort(),
    viajes: raw.viajes
      .map(v => ({ ...v, fecha: dn(v.fecha), emision: dn(v.emision), vence: dn(v.vence), cobro: v.cobro ? dn(v.cobro) : null, neto: v.flete - v.descuento }))
      .sort((a, b) => a.fecha - b.fecha),
    gastosMes: raw.gastosMes.filter(g => mesIdx.has(g.mes)).map(g => ({ ...g, mes: mesIdx.get(g.mes)! })),
    gastosDia: raw.gastosDia.map(g => ({ ...g, fecha: dn(g.fecha) })),
    gasoil: meses.map(M => raw.gasoil.find(g => g.mes === M.key) ?? { mes: M.key, lista: 0, final: 0 }),
  };
}
