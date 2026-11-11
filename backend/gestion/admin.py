from django.contrib import admin

from .models import (
    General, Parametros, Provincia, Localidad, LegajoPersonal, Choferes, Sueldos, Clientes,
    TipoServicio, TipoCubierta, Modelo, Camiones, Recorridos, Facturas, Viajes, Cobranzas, RubroCosto, Gastos,
)
from . import formulas as fx


class SafeSearchAdmin(admin.ModelAdmin):
    """ModelAdmin cuyo search_fields mezcla texto con algun campo
    FK '__exact' (codigo). Si el termino buscado no es numerico, ese
    campo explota al intentar castearlo a numero, asi que en ese caso
    se reintenta la busqueda sin los campos '__exact'."""

    def get_search_results(self, request, queryset, search_term):
        try:
            return super().get_search_results(request, queryset, search_term)
        except ValueError:
            original_search_fields = self.search_fields
            self.search_fields = [f for f in original_search_fields if not f.endswith('__exact')]
            try:
                return super().get_search_results(request, queryset, search_term)
            finally:
                self.search_fields = original_search_fields


def parametros_actuales():
    return Parametros.objects.order_by('-par_desd').first() or Parametros()


#-----------------------------------------------------------------GENERAL↓------------------------------------------------------------------------------------

@admin.register(General)
class GeneralAdmin(admin.ModelAdmin):
    list_display = ['gen_codi', 'gen_nomb']
    search_fields = ['gen_codi', 'gen_nomb']
    ordering = ['gen_nomb']


@admin.register(Parametros)
class ParametrosAdmin(admin.ModelAdmin):
    list_display = ['par_codi', 'par_desd', 'par_iibb', 'par_muni', 'par_gana', 'par_kmre', 'par_kman', 'par_scar', 'par_dola']
    ordering = ['-par_desd']


@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ['pci_codi', 'pci_nomb']
    search_fields = ['pci_codi', 'pci_nomb']
    ordering = ['pci_nomb']


@admin.register(Localidad)
class LocalidadAdmin(SafeSearchAdmin):
    list_display = ['loc_codi', 'loc_nomb', 'loc_cpos', 'pci_codi']
    list_filter = ['pci_codi']
    search_fields = ['loc_codi', 'loc_nomb']
    ordering = ['loc_nomb']


#-----------------------------------------------------------------PERSONAL↓--------------------------------------------------------------------------------

@admin.register(LegajoPersonal)
class LegajoPersonalAdmin(admin.ModelAdmin):
    list_display = ['per_codi', 'per_nomb', 'chofer_display']
    search_fields = ['per_codi', 'per_nomb']
    ordering = ['per_nomb']

    @admin.display(description='Chofer')
    def chofer_display(self, obj):
        return getattr(obj, 'chofer', None) or '- (administración)'


@admin.register(Choferes)
class ChoferesAdmin(admin.ModelAdmin):
    list_display = ['cho_codi', 'cho_nomb', 'per_codi']
    search_fields = ['cho_codi', 'cho_nomb']
    ordering = ['cho_nomb']


@admin.register(Sueldos)
class SueldosAdmin(SafeSearchAdmin):
    list_display = ['sue_codi', 'sue_mes', 'per_codi', 'sue_itot', 'sue_kmre', 'sue_kman', 'por_km_display', 'fijo_display']
    list_filter = ['sue_mes']
    search_fields = ['sue_codi', 'per_codi__per_nomb']
    ordering = ['-sue_mes', 'per_codi']

    @admin.display(description='Por km (U)')
    def por_km_display(self, obj):
        return round(fx.sueldo_variable(obj, parametros_actuales()), 2)

    @admin.display(description='Fijo (T)')
    def fijo_display(self, obj):
        return round(obj.sue_itot - fx.sueldo_variable(obj, parametros_actuales()), 2)


@admin.register(Clientes)
class ClientesAdmin(admin.ModelAdmin):
    list_display = ['cli_codi', 'cli_nomb']
    search_fields = ['cli_codi', 'cli_nomb']
    ordering = ['cli_nomb']


#-----------------------------------------------------------------CAMIONES↓--------------------------------------------------------------------------------

@admin.register(TipoServicio)
class TipoServicioAdmin(admin.ModelAdmin):
    list_display = ['tse_codi', 'tse_nomb']
    search_fields = ['tse_codi', 'tse_nomb']
    ordering = ['tse_nomb']


@admin.register(TipoCubierta)
class TipoCubiertaAdmin(admin.ModelAdmin):
    list_display = ['tcu_codi', 'tcu_nomb', 'tcu_prec', 'tcu_kdur', 'cxkm_display']
    ordering = ['tcu_codi']

    @admin.display(description='$ por km (G19:G21)')
    def cxkm_display(self, obj):
        return round(fx.costo_por_km(obj.tcu_prec, obj.tcu_kdur), 4)


@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    list_display = ['mod_codi', 'mod_nomb', 'mod_isvc', 'mod_kdur', 'cxkm_display']
    search_fields = ['mod_codi', 'mod_nomb']
    ordering = ['mod_nomb']

    @admin.display(description='Service $ por km')
    def cxkm_display(self, obj):
        return round(fx.service_por_km(obj), 4)


@admin.register(Camiones)
class CamionesAdmin(SafeSearchAdmin):
    list_display = ['cam_codi', 'cam_pate', 'cam_tipo', 'mod_codi', 'tse_codi', 'cho_codi', 'cam_acop']
    list_filter = ['cam_tipo', 'tse_codi', 'mod_codi']
    search_fields = ['cam_codi', 'cam_pate', 'cho_codi__cho_nomb']
    ordering = ['cam_pate']
    fieldsets = (
        ('Camión', {'fields': ('cam_codi', 'cam_pate', 'cam_tipo', 'mod_codi', 'tse_codi', 'cho_codi', 'cam_acop', ('cam_alta', 'cam_baja'))}),
        ('Cubiertas (Costos por dominio!E:G)', {'fields': (('cam_clin', 'cam_ctac', 'cam_ccar'),)}),
        ('Amortización', {'fields': (('cam_vusd', 'cam_vuti'),)}),
    )


#-------------------------------------------------------------------------VIAJES↓---------------------------------------------------------------------------------

class ViajesDelRecorridoInline(admin.TabularInline):
    model = Viajes
    fk_name = 'rec_codi'
    extra = 0
    fields = ['via_codi', 'via_fech', 'cli_codi', 'loc_orig', 'loc_dest', 'via_kcar', 'via_flet']
    show_change_link = True


@admin.register(Recorridos)
class RecorridosAdmin(SafeSearchAdmin):
    inlines = [ViajesDelRecorridoInline]
    list_display = ['rec_codi', 'rec_fein', 'rec_fefi', 'cam_codi', 'rec_tkms', 'rec_suml', 'prom_display']
    list_filter = ['rec_fein', 'cam_codi']
    search_fields = ['rec_codi', 'cam_codi__cam_pate']
    ordering = ['-rec_fein', '-rec_codi']

    @admin.display(description='L/100 km')
    def prom_display(self, obj):
        return fx.litros_cada_100km(obj.rec_suml, obj.rec_tkms)


class ViajesInline(admin.TabularInline):
    model = Viajes
    fk_name = 'fac_codi'
    extra = 0
    fields = ['via_codi', 'via_fech', 'cam_codi', 'via_flet', 'via_desc', 'via_itot']
    show_change_link = True


class CobranzasInline(admin.TabularInline):
    model = Cobranzas
    fk_name = 'fac_codi'
    extra = 1
    fields = ['cob_codi', 'cob_fech', 'cob_itot']


@admin.register(Facturas)
class FacturasAdmin(SafeSearchAdmin):
    inlines = [ViajesInline, CobranzasInline]
    list_display = ['fac_codi', 'fac_nume', 'fac_emis', 'fac_venc', 'cli_codi', 'gen_codi']
    list_filter = ['gen_codi', 'fac_emis']
    search_fields = ['fac_codi', 'fac_nume', 'cli_codi__cli_nomb']
    ordering = ['-fac_emis', '-fac_codi']


@admin.register(Viajes)
class ViajesAdmin(SafeSearchAdmin):
    list_display = ['via_codi', 'via_fech', 'cam_codi', 'cho_codi', 'cli_codi', 'loc_orig', 'loc_dest', 'via_kcar', 'via_flet', 'neto_display', 'fac_codi']
    list_filter = ['via_anul', 'via_fech', 'gen_codi', 'tse_codi', 'cam_codi']
    search_fields = ['via_codi', 'cam_codi__cam_pate', 'cli_codi__cli_nomb', 'cho_codi__cho_nomb', 'fac_codi__fac_nume']
    ordering = ['-via_fech', '-via_codi']
    autocomplete_fields = ['cam_codi', 'cli_codi', 'cho_codi', 'loc_orig', 'loc_dest', 'fac_codi', 'rec_codi']

    @admin.display(description='Neto')
    def neto_display(self, obj):
        return fx.neto_viaje(obj.via_flet, obj.via_desc)


@admin.register(Cobranzas)
class CobranzasAdmin(SafeSearchAdmin):
    list_display = ['cob_codi', 'cob_fech', 'fac_codi', 'cob_itot']
    list_filter = ['cob_fech']
    search_fields = ['cob_codi', 'fac_codi__fac_nume']
    ordering = ['-cob_fech']


#------------------------------------------------------------------GASTOS↓-------------------------------------------------------------------------------

@admin.register(RubroCosto)
class RubroCostoAdmin(admin.ModelAdmin):
    list_display = ['rco_codi', 'rco_nomb', 'rco_vari', 'rco_mens']
    search_fields = ['rco_codi', 'rco_nomb']
    ordering = ['rco_codi']


@admin.register(Gastos)
class GastosAdmin(SafeSearchAdmin):
    list_display = ['gas_codi', 'gas_fech', 'rco_codi', 'cam_codi', 'gas_conc', 'gas_neto', 'gas_litr', 'gas_cmes']
    list_filter = ['rco_codi', 'gas_fech', 'cam_codi']
    search_fields = ['gas_codi', 'gas_conc', 'cam_codi__cam_pate']
    ordering = ['-gas_fech', '-gas_codi']
