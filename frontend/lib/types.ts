/* =====================================================================
   CONTRATO DE DATOS
   Es lo que el backend tiene que devolver en GET /api/dataset (JSON).
   Fechas como 'YYYY-MM-DD' y meses como 'YYYY-MM'.
   ===================================================================== */

export type Servicio = 'Carretón' | 'Bitren' | 'Batea cereal' | 'Camilla' | 'Servicio de grúa' | string;

export type Rubro =
  | 'Combustible' | 'Choferes (fijo)' | 'Choferes (por km)' | 'Administración' | 'Gastos generales' | 'Impuestos'
  | 'Amortización' | 'Mantenimiento' | 'Cubiertas' | 'Service' | 'Seguros' | 'Patente y rentas';

/** Costos por dominio → columnas DOMINIO, MODELO; Sueldos x km → Chofer */
export interface RawUnidad { id: string; modelo: string; servicio: Servicio; chofer: string }

export interface RawCliente { nombre: string }

/** Detalles viajes (tabla Det.Via.Nov) + datos de facturación/cobranza (nuevos) */
export interface RawViaje {
  id: number;
  fecha: string;
  unidad: string;           // Dominio Camion
  chofer: string;
  cliente: string;
  empresa: string;          // razón social que factura
  servicio: Servicio;       // Tipo Carga Desc
  origen: string;
  destino: string;
  kmCargado: number;        // Kms
  kmReal: number;           // km del viaje incluida la vuelta (Combustible[Km Reales] prorrateado)
  flete: number;
  descuento: number;
  total: number;            // total con IVA (Det.Via.Nov → Total)
  costoCubKm: number;       // Costos variables → CUB: $/km de cubiertas para el equipo
  costoServiceKm: number;   // Costos variables → SERVICE: $/km según modelo
  factura: string;          // nuevo
  emision: string;          // nuevo
  vence: string;            // nuevo
  cobro: string | null;     // nuevo
}

/** Gastos que se devengan por mes (sueldos, seguros, patentes, amortización, costos varios, impuestos) */
export interface RawGastoMes { mes: string; rubro: Rubro; unidad: string | null; concepto: string; monto: number; variable: boolean }

/** Gastos con fecha (cargas de gasoil, reparaciones) */
export interface RawGastoDia { fecha: string; rubro: Rubro; unidad: string | null; concepto: string; monto: number; litros?: number }

/** Por mes: lista = facturado por litro con impuestos, final = costo sin IVA (Costos variables!H11 y H14, con las compras reales) */
export interface RawGasoil { mes: string; lista: number; final: number }

export interface RawDataset {
  fechaCorte: string;
  fuente: string;           // texto que se muestra como "Fuente" (DATASET_FUENTE del backend)
  unidades: RawUnidad[];
  clientes: RawCliente[];
  viajes: RawViaje[];
  gastosMes: RawGastoMes[];
  gastosDia: RawGastoDia[];
  gasoil: RawGasoil[];
}

/* ---------- Forma interna (fechas como número de día) ---------- */
export interface Mes { y: number; m: number; start: number; end: number; days: number; key: string; label: string }
export interface Viaje extends Omit<RawViaje, 'fecha' | 'emision' | 'vence' | 'cobro'> {
  fecha: number; emision: number; vence: number; cobro: number | null; neto: number;
}
export interface GastoMes extends Omit<RawGastoMes, 'mes'> { mes: number }
export interface GastoDia extends Omit<RawGastoDia, 'fecha'> { fecha: number }
export interface Dataset {
  fuente: string;
  hoy: number;
  inicio: number;
  meses: Mes[];
  unidades: RawUnidad[];
  clientes: string[];
  servicios: string[];
  empresas: string[];
  viajes: Viaje[];
  gastosMes: GastoMes[];
  gastosDia: GastoDia[];
  gasoil: RawGasoil[];
}

export interface Filtros {
  desde: number; hasta: number; preset: string;
  empresa: string; servicio: string; unidad: string; chofer: string; cliente: string;
}
