/* =====================================================================
   ORIGEN DE CADA DATO
   [tipo, fórmula o celda del Excel, nota]
   excel  = igual que en PLANILLA COSTO MAYO
   adapt  = sale del Excel con un cambio
   nuevo  = no está en la planilla
   ===================================================================== */
export type TipoOrigen = 'excel' | 'adapt' | 'nuevo';
export type Origen = [TipoOrigen, string, string?];

export const TAG_LABEL: Record<TipoOrigen, string> = { excel: 'Del Excel', adapt: 'Adaptado', nuevo: 'Nuevo' };

export const KPI_ORIGEN: Record<string, Origen> = {
  'Facturación neta': ['excel', 'SUM(Det.Via.Nov[Flete]) − SUM(Det.Via.Nov[Descuento])  ·  Costos Totales!L2'],
  'Costo total': ['adapt', 'Costos Totales!C2 = SUM(B2:B11), con 12 rubros y prorrateo diario'],
  'Resultado': ['excel', "Facturación − Costos  ·  Costos Totales!L2 − L3 (gráfico 'Facturación vs costos')"],
  'Viajes': ['excel', 'Cantidad de filas de Detalles viajes  ·  Combustible[Viajes]'],
  'Km recorridos': ['excel', 'SUM(Comb[Km Reales])  ·  Costos variables!C10'],
  'Plata en la calle': ['nuevo', 'Σ Total con IVA de facturas emitidas hasta la fecha y no cobradas'],
  'Km cargados': ['excel', 'SUBTOTAL(109, Det.Via.Nov[Kms])'],
  'Km vacíos': ['nuevo', '(Km reales − Km cargados) ÷ Km reales  ·  cruza Combustible con Detalles viajes'],
  'Facturación promedio por viaje': ['nuevo', 'Facturación neta ÷ cantidad de viajes'],
  'Ingreso por km': ['excel', 'NETO.X.DOM[FACTURADO X DOM X KM] = (SUMIF Flete − SUMIF Descuento) ÷ KM'],
  'Descuentos': ['excel', 'Det.Via.Nov[[#Totals],[Descuento]]'],
  'Unidades activas': ['excel', "Costos variables!D42 = COUNTIF('Costos por dominio'!Q5:Q24,\"<>0\")"],
  'Costo por km': ['excel', 'COSTOS.DOM[TOTAL X KM], ponderado por km de cada unidad'],
  'Consumo promedio': ['excel', 'Combustible[Prom.Comb] = Tot.Comb ÷ Km Reales × 100'],
  'Reparaciones': ['excel', 'Mantenimiento!E (mes)  ·  Costos Totales!B1 = Mantenimiento!L10'],
  'Costo de unidades paradas': ['adapt', 'COSTOS.DOM[TOTAL DOM PARADO] = patente + rentas + seguro si KM = 0. Acá suma también chofer y amortización'],
  'Costo de choferes': ['excel', 'SUMIF(Sueldos[Puesto],"Chofer",Sueldos[Monto])  ·  Costos Totales!B7'],
  'Choferes con viajes': ['nuevo', 'Choferes con al menos un viaje en el período'],
  'Parte fija': ['excel', 'Sueldos!T = TOTAL − VARIABLE ;  VARIABLE (U) = $KM REC × KM REC + $KM ANCHO × KM ANCHO'],
  'Sueldo por km': ['excel', "'Sueldos x km'!J = Sueldo ÷ km reales del camión"],
  'Administración': ['excel', 'SUMIF(Sueldos[Puesto],"Admin",Sueldos[Monto])  ·  Costos Totales!B5'],
  'Costo fijo': ['nuevo', 'Rubros que no dependen de km ni de facturación'],
  'Costo variable': ['nuevo', 'Combustible + Cubiertas + Service + Choferes por km + Impuestos'],
  'Gasoil por litro': ['adapt', 'Costos variables!H14, pero con las compras reales: Σ total sin IVA ÷ Σ litros del mes'],
  'Litros cargados': ['excel', 'SUM(Comb[Tot.Comb])  ·  Costos variables!C12'],
  'Vencido': ['nuevo', 'Saldo de facturas con vencimiento anterior a la fecha'],
  'A vencer': ['nuevo', 'Saldo de facturas todavía no vencidas'],
  'Más de 60 días': ['nuevo', 'Saldo con más de 60 días de atraso sobre el vencimiento'],
  'Días de calle': ['nuevo', 'Saldo ÷ (facturación con IVA de los últimos 90 días ÷ 90)'],
  'Cobrado en el período': ['nuevo', 'Σ facturas con fecha de cobro dentro del rango'],
};

export const PANEL_ORIGEN: Record<string, Origen> = {
  'r-evol': ['adapt', 'Facturación = Σ (Flete − Descuento) ;  Costo = Σ rubros devengados', "Es el gráfico 'Facturación vs costos' de Costos Totales (K2:L3), que en el Excel es un solo mes. Acá se abre por día, semana o mes según el rango."],
  'r-alerts': ['nuevo', 'Pierde: NETO.X.DOM[NETO X DOM] < 0\nSin viajes: KM = 0 (TOTAL DOM PARADO)\nDeuda: atraso > 60 días\nConsumo: L/100 km > promedio general × 1,15\nMargen: resultado ÷ facturación < 10 %', 'Reglas automáticas armadas sobre los cálculos del Excel. Los umbrales se pueden ajustar.'],
  'r-units': ['excel', 'NETO.X.DOM[NETO X DOM] = (FACTURADO X DOM X KM − COSTO X DOMINIO X KM) × KM MAYO', "Es el gráfico de barras de 'Costos por dominio' (AD5:AE24, facturado contra costo por dominio), expresado como resultado neto."],
  'r-grupos': ['adapt', 'Costos Totales!B1:B11 agrupados:\nCombustible · Personal (choferes + admin) · Mantenimiento y desgaste (mant + cubiertas + service)\nAmortización y seguros (amort + seguro + patente/rentas) · Estructura e impuestos (varios + IIBB/muni/ganancias)', 'La barra fijo/variable es nueva: el Excel no clasifica los rubros así.'],
  'o-evol': ['nuevo', 'Σ (Flete − Descuento) agrupado por Det.Via.Nov[Fecha]', 'El Excel tiene la fecha de cada viaje pero no la agrupa.'],
  'o-dow': ['nuevo', 'Viajes por día de la semana ÷ cantidad de esos días en el rango'],
  'o-serv': ['adapt', 'Ingreso/km = Σ Neto ÷ Σ km reales del servicio\nCosto/km = Σ (km real del viaje × COSTOS.DOM[TOTAL X KM] de su unidad) ÷ Σ km reales', 'El servicio sale de Det.Via.Nov[Tipo Carga Desc]. La planilla de Proyección calcula el costo por servicio, pero proyectado y no real.'],
  'o-cli': ['nuevo', 'SUMIF(Det.Via.Nov[Cliente], cliente, Flete − Descuento)\nMargen estimado = 1 − Σ(km real × costo/km unidad) ÷ facturado'],
  'o-rutas': ['nuevo', 'Agrupa Det.Via.Nov por Origen → Destino: viajes, km promedio (Kms), ingreso por km'],
  'o-viajes': ['adapt', "Hoja 'Detalles viajes mayo' (tabla Det.Via.Nov): Fecha, Origen, Destino, Cliente, Chofer, Dominio Camión, Tipo Carga, Kms, Flete, Descuento", 'La columna Cobro es nueva: necesita la fecha de cobro de cada factura.'],
  'f-units': ['adapt', 'Viajes y Km: Combustible[Viajes], [Km Reales]\nL/100 km: Combustible[Prom.Comb]\nIngreso/km: NETO.X.DOM[FACTURADO X DOM X KM]\nCosto/km: COSTOS.DOM[TOTAL X KM]\nResultado: NETO.X.DOM[NETO X DOM]', 'El % de km vacíos y la columna Estado son nuevos (umbral de margen bajo: 15 %).'],
  'f-desg': ['excel', 'Columnas de COSTOS.DOM, todas ÷ KM:\nJ  $ L GASOIL X KM = TOTAL COMB × $ litro ÷ KM\nL  SUELDO CHOFER ÷ KM   ·   I  SERVICE X KM (VLOOKUP modelo)\nU  CUBIERTAS X KM (VLOOKUP CUB × cantidad)   ·   Y  MANT ÷ KM\nR/S  SEGURO UNIDAD Y CARGA ÷ KM   ·   V/W  RENTAS Y PATENTE ÷ KM\nCostos varios!G4 (admin ÷ km)  ·  Costos varios!C27 (varios ÷ km)  ·  Costos variables!I37:I38 (amortización)\nAA  TOTAL X KM = SUM(...)', 'Los colores agrupan los rubros en los mismos 5 bloques de Facturación vs costos. La tabla de abajo los muestra uno por uno.'],
  'f-trend': ['nuevo', 'COSTOS.DOM[TOTAL X KM] calculado mes por mes', "Necesita historial. La hoja 'Acumulado' del Excel está pensada para esto pero está vacía."],
  'f-comb': ['excel', 'Combustible[Prom.Comb] = Tot.Comb ÷ Km Reales × 100', 'En naranja, los dominios que superan el promedio general en más de 15 % (nuevo).'],
  'f-mant': ['adapt', 'Mantenimiento!E por patente (camión + equipo enganchado: F = E camión + E acoplado)', 'En el Excel es un monto por mes. Acá cada arreglo tiene fecha y concepto, que es un dato nuevo a cargar.'],
  'p-tbl': ['excel', "Sueldos!T  FIJO = TOTAL − VARIABLE\nSueldos!U  VARIABLE = O × R + P × S  ($40,56 × km rec + $30,42 × km ancho)\n'Sueldos x km'!K  Facturado por chofer = SUMIF(Chofer, Flete) − SUMIF(Chofer, Descuento)\n'Sueldos x km'!J  Sueldo ÷ km", 'La incidencia (sueldo ÷ facturado) y sus umbrales (20 % y 30 %) son nuevos.'],
  'p-bar': ['excel', "'Sueldos x km'!G (Sueldo) contra 'Sueldos x km'!K (Facturado por chofer)"],
  'p-evol': ['nuevo', 'Choferes fijo + por km + Administración, mes por mes', 'Necesita guardar los sueldos de cada mes (hoy la planilla se pisa todos los meses).'],
  'g-rub': ['adapt', 'Costos Totales!B1:B11:\nMantenimiento (B1) · Rentas (B2) · Patente (B3) · Seguro (B4) · Administración (B5) · Varios (B6)\nChoferes (B7) · Combustible (B8 = litros × $ litro) · Service (B9) · Cubiertas (B10) · Amortización (B11)', 'Cambios: Choferes separado en fijo y por km, impuestos separados de Varios, rentas y patente juntas. La amortización se calcula bien: en el Excel B11 apunta a una celda vacía.'],
  'g-split': ['nuevo', 'Variable = Combustible + Cubiertas + Service + Choferes por km + Impuestos\nFijo = el resto', 'Clasificación propia. El Excel solo separa fijo/variable dentro de los sueldos.'],
  'g-evol': ['nuevo', 'Los mismos rubros de Costos Totales, tramo por tramo, apilados en 5 bloques', "Reemplaza a la hoja 'Acumulado', que está vacía."],
  'g-gas': ['adapt', 'Excel: Costos variables!H14 = H11 ÷ 1,16 − H13 (lista ÷ 1,16 − crédito)\nAcá, con las compras de gasoil del mes:\n  facturado por litro = Σ importe total ÷ Σ litros\n  costo final = Σ total sin IVA ÷ Σ litros', 'El precio real reemplaza la estimación del Excel. La serie mes a mes es nueva: en el Excel se pisa el precio cada mes.'],
  'g-est': ['excel', 'Costos varios!B5:B23 (alquiler, publicidad, honorarios, peajes…)\nB24 IIBB = E6 × 2 %   ·   B25 Municipalidad = E6 × 0,2 %   ·   B26 Ganancias = E6 × 6 %\nE6 = Det.Via.Nov[Flete] − [Descuento]\nAdministración: SUMIF(Sueldos[Puesto],"Admin")  ·  $/km = monto ÷ Costos variables!C10'],
  'c-aging': ['nuevo', "Atraso = fecha 'hasta' − vencimiento de la factura\nTramos: a vencer · 1–30 · 31–60 · más de 60 días", 'Para usarlo con datos reales hay que cargar por factura: número, emisión, vencimiento y fecha de cobro.'],
  'c-saldo': ['nuevo', 'Saldo al cierre de cada mes = Σ facturas emitidas hasta esa fecha y no cobradas a esa fecha'],
  'c-fact': ['nuevo', 'Factura, cliente, emisión, vencimiento, días de atraso, Total con IVA (Det.Via.Nov[Total])', 'El Total con IVA sí está en el Excel: (Flete − Descuento + Seguro + Adicionales) × 1,21.'],
};

export const VISTAS = [
  { slug: 'facturacion', nombre: 'Facturación vs costos', origen: ['adapt', 'Cruza Detalles viajes, Costos por dominio y Costos Totales'] },
  { slug: 'viajes', nombre: 'Detalles viajes', origen: ['excel', 'Detalles viajes mayo (tabla Det.Via.Nov)'] },
  { slug: 'dominios', nombre: 'Costos por dominio', origen: ['excel', 'Costos por dominio (COSTOS.DOM, NETO.X.DOM), Combustible y Mantenimiento'] },
  { slug: 'sueldos', nombre: 'Sueldos', origen: ['excel', 'Sueldos y Sueldos x km'] },
  { slug: 'costos', nombre: 'Costos totales', origen: ['excel', 'Costos variables, Costos varios y Costos Totales'] },
  { slug: 'cobranzas', nombre: 'Cobranzas', origen: ['nuevo', 'No existe en la planilla. Requiere datos de facturación y cobro'] },
] as const satisfies readonly { slug: string; nombre: string; origen: readonly [TipoOrigen, string] }[];
