from django.db import models

# Estructura del Tablero Murray.
# Regla: cada campo es UN dato que se carga (sale de la PLANILLA COSTO MAYO o, si dice "nuevo", no está en el Excel).
# No hay campos de respaldo ni duplicados: lo que se puede calcular, lo calcula el backend (dataset.py / formulas.py).


#---------------------------------------------------------GENERAL↓------------------------------------------------------------------------

class General(models.Model):
    """Razón social que factura. Det.Via.Nov → Empresa. Filtro "Razón social"."""
    gen_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código de la empresa")
    gen_nomb = models.CharField(max_length=150, help_text="Nombre de la empresa (ej. SURPATRIC S.A.)")

    def __str__(self):
        return self.gen_nomb


class Parametros(models.Model):
    """Valores fijos de la planilla. Se usa el último vigente en cada mes."""
    par_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código")
    par_desd = models.DateField(help_text="Vigente desde")
    par_iibb = models.DecimalField(max_digits=10, decimal_places=4, default=2, help_text="Ingresos brutos % sobre lo facturado — Costos varios!E9")
    par_muni = models.DecimalField(max_digits=10, decimal_places=4, default=0.2, help_text="Tasa municipal % sobre lo facturado — Costos varios!E10")
    par_gana = models.DecimalField(max_digits=10, decimal_places=4, default=6, help_text="Ganancias % sobre lo facturado — Costos varios!E11")
    par_kmre = models.DecimalField(max_digits=30, decimal_places=2, default=40.56, help_text="Sueldo: $ por km recorrido — Sueldos!O ($ KM REC)")
    par_kman = models.DecimalField(max_digits=30, decimal_places=2, default=30.42, help_text="Sueldo: $ por km con carga ancha — Sueldos!P ($ KM ANCHO)")
    par_scar = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Seguro de carga anual por camión — Costos por dominio!P")
    par_dola = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Cotización del dólar — Costos variables!C16")

    def __str__(self):
        return f"Parámetros desde {self.par_desd}"


#----------------------------------------------------------LOCALIDADES↓-----------------------------------------------------------------------

class Provincia(models.Model):
    pci_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código de la provincia")
    pci_nomb = models.CharField(max_length=100, blank=True, null=True, help_text="Nombre de la provincia")

    def __str__(self):
        return self.pci_nomb or f"Provincia {self.pci_codi}"


class Localidad(models.Model):
    """Det.Via.Nov → Cod.Origen / Origen y Cod.Destino / Destino."""
    loc_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código de la localidad")
    loc_nomb = models.CharField(max_length=100, help_text="Nombre de la localidad (ej. RIO CUARTO)")
    loc_cpos = models.IntegerField(blank=True, null=True, help_text="Código postal")
    pci_codi = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name="localidades", null=True, blank=True, help_text="Provincia")

    def __str__(self):
        return self.loc_nomb


#----------------------------------------------------------PERSONAL↓--------------------------------------------------------------------------

class LegajoPersonal(models.Model):
    """Todo el que cobra sueldo (hoja Sueldos → Nombres Empleados). Los que no son choferes son Administración."""
    per_codi = models.IntegerField(primary_key=True, editable=True, help_text="Número de legajo")
    per_nomb = models.CharField(max_length=100, help_text="Nombre del empleado")

    def __str__(self):
        return self.per_nomb


class Choferes(models.Model):
    """Det.Via.Nov → Cod.Chofer / Chofer. Filtro "Chofer" y tabla Sueldos x km."""
    cho_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código del chofer (Cod.Chofer)")
    cho_nomb = models.CharField(max_length=100, help_text="Nombre del chofer")
    per_codi = models.OneToOneField(LegajoPersonal, on_delete=models.PROTECT, related_name="chofer", null=True, blank=True, help_text="Su legajo, para unirlo con su recibo de sueldo")

    def __str__(self):
        return self.cho_nomb


class Sueldos(models.Model):
    """
    Hoja Sueldos: un recibo por empleado y mes.
    El backend calcula:  POR KM = par_kmre × sue_kmre + par_kman × sue_kman   ·   FIJO = sue_itot − POR KM
    """
    sue_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código del recibo")
    sue_mes = models.DateField(help_text="Mes liquidado (día 1 del mes) — Sueldos!B")
    sue_itot = models.DecimalField(max_digits=30, decimal_places=2, help_text="Total del recibo — Sueldos!Q (TOTAL)")
    sue_kmre = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Km recorridos que paga el recibo — Sueldos!R (KM REC)")
    sue_kman = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Km con carga ancha que paga el recibo — Sueldos!S")
    per_codi = models.ForeignKey(LegajoPersonal, on_delete=models.PROTECT, related_name="sueldos", help_text="Empleado")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["per_codi", "sue_mes"], name="uk_sueldo")]

    def __str__(self):
        return f"Sueldo {self.per_codi} {self.sue_mes:%m/%Y}"


#----------------------------------------------------------CLIENTES↓--------------------------------------------------------------------------

class Clientes(models.Model):
    """Det.Via.Nov → Cod.Clie / Cliente. Filtro "Cliente"."""
    cli_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código del cliente (Cod.Clie)")
    cli_nomb = models.CharField(max_length=100, help_text="Nombre del cliente")

    def __str__(self):
        return self.cli_nomb


#----------------------------------------------------------CAMIONES↓--------------------------------------------------------------------------

class TipoServicio(models.Model):
    """Det.Via.Nov → Tipo Carga Cod / Tipo Carga Desc (CARRETON, BITREN, BATEA CEREAL, CAMILLA…). Filtro "Servicio"."""
    tse_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código del tipo de carga")
    tse_nomb = models.CharField(max_length=100, help_text="Nombre del servicio")
    # Costos variables!L24:P27 (Referencias y cantidad por eje) → "Costo cubiertas" C24:D27 = Σ cantidad × $/km del tipo
    tse_clin = models.IntegerField(default=0, help_text="Cubiertas LINEAL del equipo — Costos variables!N25:N27")
    tse_ctac = models.IntegerField(default=0, help_text="Cubiertas TACO del equipo — Costos variables!P25")
    tse_ccar = models.IntegerField(default=0, help_text="Cubiertas CARRETÓN del equipo — Costos variables!N24")

    def __str__(self):
        return self.tse_nomb


class TipoCubierta(models.Model):
    """Costos variables!C19:F21. El backend calcula $/km = precio ÷ duración."""
    tcu_codi = models.IntegerField(primary_key=True, editable=True, help_text="1 lineal, 2 taco, 3 carretón")
    tcu_nomb = models.CharField(max_length=50, help_text="Tipo (LINEAL, TACO, CARRETON)")
    tcu_prec = models.DecimalField(max_digits=30, decimal_places=2, help_text="Precio de una cubierta — $ UNITARIO")
    tcu_kdur = models.DecimalField(max_digits=30, decimal_places=2, help_text="Km que dura — DURACIÓN KM PROM")

    def __str__(self):
        return self.tcu_nomb


class Modelo(models.Model):
    """Costos variables!C30:E34 (SERVICE). El backend calcula $/km = precio del service ÷ km."""
    mod_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código del modelo")
    mod_nomb = models.CharField(max_length=100, help_text="Modelo (VOLVO, VOLVO 310, FORD, SCANIA V8, IVECO)")
    mod_isvc = models.DecimalField(max_digits=30, decimal_places=2, help_text="Precio de un service — $ UNITARIO")
    mod_kdur = models.DecimalField(max_digits=30, decimal_places=2, help_text="Cada cuántos km se hace — KM DURACIÓN")

    def __str__(self):
        return self.mod_nomb


class Camiones(models.Model):
    """Costos por dominio → DOMINIO. Un registro por camión y por acoplado/carretón/batea. Filtro "Dominio"."""
    TIPOS = [('C', 'Camión'), ('A', 'Acoplado / carretón / batea / semi')]
    cam_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código (Det.Via.Nov → Cod.Camion / Cod.Acop)")
    cam_pate = models.CharField(max_length=20, unique=True, help_text="Patente (ej. AE 412 KT)")
    cam_tipo = models.CharField(max_length=1, choices=TIPOS, default='C', help_text="C = camión, A = acoplado")
    cam_clin = models.IntegerField(default=0, help_text="Cubiertas LINEAL que lleva — Costos por dominio!E")
    cam_ctac = models.IntegerField(default=0, help_text="Cubiertas TACO que lleva — Costos por dominio!F")
    cam_ccar = models.IntegerField(default=0, help_text="Cubiertas CARRETÓN que lleva — Costos por dominio!G")
    cam_vusd = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Valor en U$S — Costos variables!E37:E38 (amortización)")
    cam_vuti = models.IntegerField(default=120, help_text="Meses en que se amortiza — Costos variables!L36")
    cam_alta = models.DateField(blank=True, null=True, help_text="Desde cuándo está en la flota")
    cam_baja = models.DateField(blank=True, null=True, help_text="Hasta cuándo (vacío = sigue activo)")
    mod_codi = models.ForeignKey(Modelo, on_delete=models.PROTECT, related_name="camiones", null=True, blank=True, help_text="Modelo (solo camiones) — Costos por dominio!D")
    tse_codi = models.ForeignKey(TipoServicio, on_delete=models.PROTECT, related_name="camiones", null=True, blank=True, help_text="Servicio que hace (solo camiones)")
    cho_codi = models.ForeignKey(Choferes, on_delete=models.PROTECT, related_name="camiones", null=True, blank=True, help_text="Chofer asignado (solo camiones) — Sueldos x km")
    cam_acop = models.ForeignKey('self', on_delete=models.PROTECT, related_name="camiones_que_lo_llevan", null=True, blank=True, help_text="Acoplado que lleva (solo camiones)")

    def __str__(self):
        return self.cam_pate


#--------------------------------------------------------VIAJES↓---------------------------------------------------------------------------

class Recorridos(models.Model):
    """Hoja Combustible: km reales (con la vuelta) y litros de cada salida de un camión."""
    rec_codi = models.IntegerField(primary_key=True, editable=True, help_text="Número de recorrido")
    rec_fein = models.DateField(help_text="Fecha de salida")
    rec_fefi = models.DateField(help_text="Fecha de vuelta")
    rec_tkms = models.DecimalField(max_digits=30, decimal_places=2, help_text="Km reales recorridos — Combustible → Km Reales")
    rec_suml = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Litros de gasoil cargados — Combustible → Tot.Comb")
    cam_codi = models.ForeignKey(Camiones, on_delete=models.PROTECT, related_name="recorridos", help_text="Camión")

    def __str__(self):
        return f"Recorrido {self.rec_codi} - {self.cam_codi}"


class Facturas(models.Model):
    """Nuevo (no está en el Excel). Para Cobranzas. El total es la suma del total con IVA de sus viajes."""
    fac_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código de la factura")
    fac_nume = models.CharField(max_length=30, help_text="Número (ej. A-0003-00004120)")
    fac_emis = models.DateField(help_text="Fecha de emisión")
    fac_venc = models.DateField(help_text="Fecha de vencimiento")
    cli_codi = models.ForeignKey(Clientes, on_delete=models.PROTECT, related_name="facturas", help_text="Cliente")
    gen_codi = models.ForeignKey(General, on_delete=models.PROTECT, related_name="facturas", help_text="Empresa que factura")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["gen_codi", "fac_nume"], name="uk_factura")]

    def __str__(self):
        return f"Factura {self.fac_nume}"


class Viajes(models.Model):
    """Hoja Detalles viajes (Det.Via.Nov). Un registro por viaje."""
    via_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código del viaje (Cod.Venta)")
    via_fech = models.DateField(help_text="Fecha")
    via_kcar = models.DecimalField(max_digits=30, decimal_places=2, help_text="Km del viaje con carga — Kms")
    via_flet = models.DecimalField(max_digits=30, decimal_places=2, help_text="Flete, sin IVA — Flete")
    via_desc = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Descuento, sin IVA — Descuento")
    via_itot = models.DecimalField(max_digits=30, decimal_places=2, help_text="Total con IVA — Total")
    via_anul = models.BooleanField(default=False, help_text="Anulado (no suma en nada) — Anulado")
    cam_codi = models.ForeignKey(Camiones, on_delete=models.PROTECT, related_name="viajes", help_text="Camión — Cod.Camion")
    cho_codi = models.ForeignKey(Choferes, on_delete=models.PROTECT, related_name="viajes", help_text="Chofer — Cod.Chofer")
    cli_codi = models.ForeignKey(Clientes, on_delete=models.PROTECT, related_name="viajes", help_text="Cliente — Cod.Clie")
    gen_codi = models.ForeignKey(General, on_delete=models.PROTECT, related_name="viajes", help_text="Empresa que factura — Empresa")
    tse_codi = models.ForeignKey(TipoServicio, on_delete=models.PROTECT, related_name="viajes", help_text="Servicio — Tipo Carga Cod")
    loc_orig = models.ForeignKey(Localidad, on_delete=models.PROTECT, related_name="viajes_origen", help_text="Origen — Cod.Origen")
    loc_dest = models.ForeignKey(Localidad, on_delete=models.PROTECT, related_name="viajes_destino", help_text="Destino — Cod.Destino")
    rec_codi = models.ForeignKey(Recorridos, on_delete=models.PROTECT, related_name="viajes", null=True, blank=True, help_text="Recorrido al que pertenece (sus km reales se reparten entre sus viajes)")
    fac_codi = models.ForeignKey(Facturas, on_delete=models.PROTECT, related_name="viajes", null=True, blank=True, help_text="Factura (vacío = todavía no se facturó)")

    def __str__(self):
        return f"Viaje {self.via_codi} - {self.cam_codi}"


class Cobranzas(models.Model):
    """Nuevo. Cobros de una factura: queda cobrada cuando la suma de sus cobros llega al total."""
    cob_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código del cobro")
    cob_fech = models.DateField(help_text="Fecha del cobro")
    cob_itot = models.DecimalField(max_digits=30, decimal_places=2, help_text="Importe cobrado, con IVA")
    fac_codi = models.ForeignKey(Facturas, on_delete=models.PROTECT, related_name="cobranzas", help_text="Factura que se cobra")

    def __str__(self):
        return f"Cobro {self.cob_codi} - {self.fac_codi}"


#--------------------------------------------------------GASTOS↓---------------------------------------------------------------------------

class RubroCosto(models.Model):
    """
    Los 12 rubros de Costos Totales. rco_nomb tiene que ser igual al del frontend (lib/engine.ts → RUBROS).
    Choferes, Amortización, Impuestos, Cubiertas, Service y Combustible los calcula el backend: no se cargan como gasto
    (de Combustible solo se cargan las compras de gasoil para sacar el precio por litro).
    """
    rco_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código del rubro")
    rco_nomb = models.CharField(max_length=100, unique=True, help_text="Nombre del rubro")
    rco_vari = models.BooleanField(default=False, help_text="Es costo variable (sí = se mueve con los km o lo facturado)")
    rco_mens = models.BooleanField(default=False, help_text="Es un gasto del mes (sí = se reparte en el mes; no = cae el día del gasto)")

    def __str__(self):
        return self.rco_nomb


class Gastos(models.Model):
    """
    Todo lo que se paga y no se calcula, sin IVA. Sale de las hojas:
      Mantenimiento (por dominio) · Costos variables!C48:G (patente, rentas y seguro por dominio)
      Costos varios (alquileres, teléfono, honorarios… sin dominio) · compras de gasoil (para el precio por litro)
    Sin dominio = gasto de estructura: el backend lo reparte entre los camiones según los km.
    """
    gas_codi = models.IntegerField(primary_key=True, editable=True, help_text="Código del gasto")
    gas_fech = models.DateField(help_text="Fecha (si el rubro es del mes, el mes de esta fecha)")
    gas_conc = models.CharField(max_length=200, help_text="Concepto (ej. Alquileres, Cambio de embrague, Seguro trimestral)")
    gas_neto = models.DecimalField(max_digits=30, decimal_places=2, help_text="Importe sin IVA (nota de crédito: negativo)")
    gas_itot = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Importe con impuestos (solo gasoil: precio de lista — Costos variables!H11)")
    gas_litr = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Litros (solo gasoil)")
    gas_cmes = models.IntegerField(default=1, help_text="Meses que cubre (seguro trimestral = 3): se reparte en partes iguales")
    rco_codi = models.ForeignKey(RubroCosto, on_delete=models.PROTECT, related_name="gastos", help_text="Rubro")
    cam_codi = models.ForeignKey(Camiones, on_delete=models.PROTECT, related_name="gastos", null=True, blank=True, help_text="Dominio (vacío = estructura)")

    def __str__(self):
        return f"{self.gas_conc} {self.gas_fech}"
