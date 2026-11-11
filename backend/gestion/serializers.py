from rest_framework import serializers

# fields = '__all__': cada serializer trae todos los campos del modelo,
# más los nombres de las tablas relacionadas (read_only) para leer la API sin cruzar códigos.
from .models import (
    General, Parametros, Provincia, Localidad, LegajoPersonal, Choferes, Sueldos, Clientes,
    TipoServicio, TipoCubierta, Modelo, Camiones, Recorridos, Facturas, Viajes, Cobranzas, RubroCosto, Gastos,
)
from . import formulas as fx


#---------------------------------------------------------GENERAL↓------------------------------------------------------------------

class GeneralSerializer(serializers.ModelSerializer):
    class Meta:
        model = General
        fields = '__all__'


class ParametrosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parametros
        fields = '__all__'


class ProvinciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provincia
        fields = '__all__'


class LocalidadSerializer(serializers.ModelSerializer):
    pci_nomb = serializers.CharField(source='pci_codi.pci_nomb', read_only=True)

    class Meta:
        model = Localidad
        fields = '__all__'


#----------------------------------------------------------PERSONAL↓--------------------------------------------------------------------

class LegajoPersonalSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegajoPersonal
        fields = '__all__'


class ChoferesSerializer(serializers.ModelSerializer):
    per_nomb = serializers.CharField(source='per_codi.per_nomb', read_only=True)

    class Meta:
        model = Choferes
        fields = '__all__'


class SueldosSerializer(serializers.ModelSerializer):
    per_nomb = serializers.CharField(source='per_codi.per_nomb', read_only=True)

    class Meta:
        model = Sueldos
        fields = '__all__'


class ClientesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clientes
        fields = '__all__'


#----------------------------------------------------------CAMIONES↓--------------------------------------------------------------------

class TipoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoServicio
        fields = '__all__'


class TipoCubiertaSerializer(serializers.ModelSerializer):
    tcu_cxkm = serializers.SerializerMethodField(help_text="Costo por km = precio ÷ duración (Costos variables!G19:G21)")

    class Meta:
        model = TipoCubierta
        fields = '__all__'

    def get_tcu_cxkm(self, obj):
        return round(fx.costo_por_km(obj.tcu_prec, obj.tcu_kdur), 4)


class ModeloSerializer(serializers.ModelSerializer):
    mod_cxkm = serializers.SerializerMethodField(help_text="Service $ por km (Costos variables!F30:F34)")

    class Meta:
        model = Modelo
        fields = '__all__'

    def get_mod_cxkm(self, obj):
        return round(fx.service_por_km(obj), 4)


class CamionesSerializer(serializers.ModelSerializer):
    mod_nomb = serializers.CharField(source='mod_codi.mod_nomb', read_only=True)
    tse_nomb = serializers.CharField(source='tse_codi.tse_nomb', read_only=True)
    cho_nomb = serializers.CharField(source='cho_codi.cho_nomb', read_only=True)
    acop_pate = serializers.CharField(source='cam_acop.cam_pate', read_only=True)

    class Meta:
        model = Camiones
        fields = '__all__'


#----------------------------------------------------------VIAJES↓----------------------------------------------------------------------

class RecorridosSerializer(serializers.ModelSerializer):
    cam_pate = serializers.CharField(source='cam_codi.cam_pate', read_only=True)
    rec_prom = serializers.SerializerMethodField(help_text="Litros cada 100 km del recorrido")

    class Meta:
        model = Recorridos
        fields = '__all__'

    def get_rec_prom(self, obj):
        return fx.litros_cada_100km(obj.rec_suml, obj.rec_tkms)


class FacturasSerializer(serializers.ModelSerializer):
    cli_nomb = serializers.CharField(source='cli_codi.cli_nomb', read_only=True)
    gen_nomb = serializers.CharField(source='gen_codi.gen_nomb', read_only=True)

    class Meta:
        model = Facturas
        fields = '__all__'


class ViajesSerializer(serializers.ModelSerializer):
    cam_pate = serializers.CharField(source='cam_codi.cam_pate', read_only=True)
    cho_nomb = serializers.CharField(source='cho_codi.cho_nomb', read_only=True)
    cli_nomb = serializers.CharField(source='cli_codi.cli_nomb', read_only=True)
    gen_nomb = serializers.CharField(source='gen_codi.gen_nomb', read_only=True)
    tse_nomb = serializers.CharField(source='tse_codi.tse_nomb', read_only=True)
    orig_nomb = serializers.CharField(source='loc_orig.loc_nomb', read_only=True)
    dest_nomb = serializers.CharField(source='loc_dest.loc_nomb', read_only=True)
    fac_nume = serializers.CharField(source='fac_codi.fac_nume', read_only=True)
    via_neto = serializers.SerializerMethodField(help_text="Flete − Descuento (Costos varios!E6)")

    class Meta:
        model = Viajes
        fields = '__all__'

    def get_via_neto(self, obj):
        return fx.neto_viaje(obj.via_flet, obj.via_desc)


class CobranzasSerializer(serializers.ModelSerializer):
    fac_nume = serializers.CharField(source='fac_codi.fac_nume', read_only=True)

    class Meta:
        model = Cobranzas
        fields = '__all__'


#----------------------------------------------------------GASTOS↓----------------------------------------------------------------------

class RubroCostoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RubroCosto
        fields = '__all__'


class GastosSerializer(serializers.ModelSerializer):
    rco_nomb = serializers.CharField(source='rco_codi.rco_nomb', read_only=True)
    cam_pate = serializers.CharField(source='cam_codi.cam_pate', read_only=True)

    class Meta:
        model = Gastos
        fields = '__all__'
