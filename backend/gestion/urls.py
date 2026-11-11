from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    api_root, dataset, importar_datos,
    GeneralViewSet, ParametrosViewSet, ProvinciaViewSet, LocalidadViewSet,
    LegajoPersonalViewSet, ChoferesViewSet, SueldosViewSet, ClientesViewSet,
    TipoServicioViewSet, TipoCubiertaViewSet, ModeloViewSet, CamionesViewSet,
    RecorridosViewSet, FacturasViewSet, ViajesViewSet, CobranzasViewSet,
    RubroCostoViewSet, GastosViewSet,
)

router = DefaultRouter()

#---------------------------------------------------------GENERAL↓------------------------------------------------------------------
router.register(r'general', GeneralViewSet, basename='general')
router.register(r'parametros', ParametrosViewSet, basename='parametros')
router.register(r'provincias', ProvinciaViewSet, basename='provincia')
router.register(r'localidades', LocalidadViewSet, basename='localidad')

#----------------------------------------------------------PERSONAL↓--------------------------------------------------------------------
router.register(r'legajos-personal', LegajoPersonalViewSet, basename='legajopersonal')
router.register(r'choferes', ChoferesViewSet, basename='chofer')
router.register(r'sueldos', SueldosViewSet, basename='sueldo')
router.register(r'clientes', ClientesViewSet, basename='cliente')

#----------------------------------------------------------CAMIONES↓--------------------------------------------------------------------
router.register(r'tipos-servicio', TipoServicioViewSet, basename='tiposervicio')
router.register(r'tipos-cubierta', TipoCubiertaViewSet, basename='tipocubierta')
router.register(r'modelos', ModeloViewSet, basename='modelo')
router.register(r'camiones', CamionesViewSet, basename='camion')

#----------------------------------------------------------VIAJES↓----------------------------------------------------------------------
router.register(r'recorridos', RecorridosViewSet, basename='recorrido')
router.register(r'facturas', FacturasViewSet, basename='factura')
router.register(r'viajes', ViajesViewSet, basename='viaje')
router.register(r'cobranzas', CobranzasViewSet, basename='cobranza')

#----------------------------------------------------------GASTOS↓----------------------------------------------------------------------
router.register(r'rubros-costo', RubroCostoViewSet, basename='rubrocosto')
router.register(r'gastos', GastosViewSet, basename='gasto')

urlpatterns = [
    path('', api_root, name='api-root'),
    path('dataset/', dataset, name='dataset'),
    path('dataset', dataset),  # el frontend pide {API}/dataset sin barra final

    path('importar_datos/', importar_datos, name='importar-datos'),
    path('', include(router.urls)),
]
