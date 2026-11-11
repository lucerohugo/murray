import json
import traceback
from datetime import date

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from .auth import clave_valida
from .dataset import armar_dataset

from .models import (
    General, Parametros, Provincia, Localidad, LegajoPersonal, Choferes, Sueldos, Clientes,
    TipoServicio, TipoCubierta, Modelo, Camiones, Recorridos, Facturas, Viajes, Cobranzas, RubroCosto, Gastos,
)
from .serializers import (
    GeneralSerializer, ParametrosSerializer, ProvinciaSerializer, LocalidadSerializer,
    LegajoPersonalSerializer, ChoferesSerializer, SueldosSerializer, ClientesSerializer,
    TipoServicioSerializer, TipoCubiertaSerializer, ModeloSerializer, CamionesSerializer,
    RecorridosSerializer, FacturasSerializer, ViajesSerializer, CobranzasSerializer, RubroCostoSerializer, GastosSerializer,
)


def health(request):
    """Público, sin datos: para Uptime Kuma y el chequeo de Docker."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'ok': False}, status=503)
    return JsonResponse({'ok': True})


@api_view(['GET'])
def api_root(request, format=None):
    endpoints = {
        'dataset': 'dataset',
        'general': 'general-list',
        'parametros': 'parametros-list',
        'provincias': 'provincia-list',
        'localidades': 'localidad-list',
        'legajos-personal': 'legajopersonal-list',
        'choferes': 'chofer-list',
        'sueldos': 'sueldo-list',
        'clientes': 'cliente-list',
        'tipos-servicio': 'tiposervicio-list',
        'tipos-cubierta': 'tipocubierta-list',
        'modelos': 'modelo-list',
        'camiones': 'camion-list',
        'recorridos': 'recorrido-list',
        'facturas': 'factura-list',
        'viajes': 'viaje-list',
        'cobranzas': 'cobranza-list',
        'rubros-costo': 'rubrocosto-list',
        'gastos': 'gasto-list',
    }
    return Response({
        key: reverse(name, request=request, format=format)
        for key, name in endpoints.items()
    })


#--------------------------------------------------------DATASET (TABLERO)↓-----------------------------------------------------------

@api_view(['GET'])
def dataset(request):
    """
    GET /api/dataset/?corte=YYYY-MM-DD
    Todo lo que necesita el tablero, con la forma de RawDataset (frontend/lib/types.ts).
    Sin "corte" toma la última fecha con viajes o gastos.
    """
    corte = request.query_params.get('corte')
    try:
        corte = date.fromisoformat(corte) if corte else None
    except ValueError:
        return Response({'detail': 'corte tiene que ser YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(armar_dataset(corte, fuente=settings.DATASET_FUENTE))


# ================================================================
# BASE VIEWSET
# ================================================================

class BaseViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


# ================================================================
# BULK CREATE MIXIN (upsert por PK propia, FK -> *_id)
# ================================================================

class BulkCreateMixin:
    """
    Permite que el POST acepte un objeto unico o una lista de objetos.
    Por cada item hace update_or_create contra su propia PK (lookup_field_name),
    convirtiendo los campos FK (ej. cam_codi) a su forma *_id para Django ORM.
    """
    lookup_field_name = None

    def create(self, request, *args, **kwargs):
        data = request.data

        if not isinstance(data, list):
            data = [data]

        resultados = []

        for item in data:
            try:
                if not item.get(self.lookup_field_name):
                    resultados.append({
                        "error": f"Falta campo {self.lookup_field_name}",
                        "data": item
                    })
                    continue

                model = self.queryset.model
                data_item = item.copy()

                for field in model._meta.fields:
                    if field.is_relation and field.many_to_one:
                        fk_name = field.name
                        if fk_name in data_item:
                            data_item[f"{fk_name}_id"] = data_item.pop(fk_name)

                obj, created = model.objects.update_or_create(
                    **{self.lookup_field_name: data_item[self.lookup_field_name]},
                    defaults={k: v for k, v in data_item.items() if v is not None}
                )

                resultados.append({
                    "id": getattr(obj, self.lookup_field_name),
                    "created": created
                })

            except Exception as e:
                resultados.append({
                    "error": str(e),
                    "data": item
                })

        return Response(resultados, status=status.HTTP_200_OK)


#---------------------------------------------------------GENERAL↓------------------------------------------------------------------

class GeneralViewSet(BulkCreateMixin, BaseViewSet):
    queryset = General.objects.all()
    serializer_class = GeneralSerializer
    lookup_field_name = 'gen_codi'
    search_fields = ['gen_nomb']
    ordering = ['gen_nomb']


class ParametrosViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Parametros.objects.all()
    serializer_class = ParametrosSerializer
    lookup_field_name = 'par_codi'
    ordering = ['-par_desd']


class ProvinciaViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer
    lookup_field_name = 'pci_codi'
    search_fields = ['pci_nomb']
    ordering = ['pci_nomb']


class LocalidadViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Localidad.objects.select_related('pci_codi')
    serializer_class = LocalidadSerializer
    lookup_field_name = 'loc_codi'
    search_fields = ['loc_nomb']
    ordering = ['loc_nomb']


#----------------------------------------------------------PERSONAL↓--------------------------------------------------------------------

class LegajoPersonalViewSet(BulkCreateMixin, BaseViewSet):
    queryset = LegajoPersonal.objects.all()
    serializer_class = LegajoPersonalSerializer
    lookup_field_name = 'per_codi'
    search_fields = ['per_nomb']
    ordering = ['per_nomb']


class ChoferesViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Choferes.objects.select_related('per_codi')
    serializer_class = ChoferesSerializer
    lookup_field_name = 'cho_codi'
    search_fields = ['cho_nomb']
    ordering = ['cho_nomb']


class SueldosViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Sueldos.objects.select_related('per_codi')
    serializer_class = SueldosSerializer
    lookup_field_name = 'sue_codi'
    search_fields = ['per_codi__per_nomb']
    ordering = ['-sue_mes', 'per_codi']
    filterset_fields = {'sue_mes': ['exact', 'gte', 'lte'], 'per_codi': ['exact']}


class ClientesViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Clientes.objects.all()
    serializer_class = ClientesSerializer
    lookup_field_name = 'cli_codi'
    search_fields = ['cli_nomb']
    ordering = ['cli_nomb']


#----------------------------------------------------------CAMIONES↓--------------------------------------------------------------------

class TipoServicioViewSet(BulkCreateMixin, BaseViewSet):
    queryset = TipoServicio.objects.all()
    serializer_class = TipoServicioSerializer
    lookup_field_name = 'tse_codi'
    search_fields = ['tse_nomb']
    ordering = ['tse_nomb']


class TipoCubiertaViewSet(BulkCreateMixin, BaseViewSet):
    queryset = TipoCubierta.objects.all()
    serializer_class = TipoCubiertaSerializer
    lookup_field_name = 'tcu_codi'
    ordering = ['tcu_codi']


class ModeloViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Modelo.objects.all()
    serializer_class = ModeloSerializer
    lookup_field_name = 'mod_codi'
    search_fields = ['mod_nomb']
    ordering = ['mod_nomb']


class CamionesViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Camiones.objects.select_related('mod_codi', 'tse_codi', 'cho_codi', 'cam_acop')
    serializer_class = CamionesSerializer
    lookup_field_name = 'cam_codi'
    search_fields = ['cam_pate', 'cho_codi__cho_nomb']
    ordering = ['cam_pate']
    filterset_fields = ['cam_tipo', 'tse_codi', 'mod_codi', 'cho_codi']


#----------------------------------------------------------VIAJES↓----------------------------------------------------------------------

class RecorridosViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Recorridos.objects.select_related('cam_codi')
    serializer_class = RecorridosSerializer
    lookup_field_name = 'rec_codi'
    search_fields = ['cam_codi__cam_pate']
    ordering = ['-rec_fein']
    filterset_fields = {'rec_fein': ['exact', 'gte', 'lte'], 'cam_codi': ['exact']}


class FacturasViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Facturas.objects.select_related('cli_codi', 'gen_codi')
    serializer_class = FacturasSerializer
    lookup_field_name = 'fac_codi'
    search_fields = ['fac_nume', 'cli_codi__cli_nomb']
    ordering = ['-fac_emis']
    filterset_fields = {'fac_emis': ['exact', 'gte', 'lte'], 'cli_codi': ['exact'], 'gen_codi': ['exact']}


class ViajesViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Viajes.objects.select_related(
        'cam_codi', 'cho_codi', 'cli_codi', 'gen_codi', 'tse_codi', 'loc_orig', 'loc_dest', 'fac_codi',
    )
    serializer_class = ViajesSerializer
    lookup_field_name = 'via_codi'
    search_fields = ['cam_codi__cam_pate', 'cli_codi__cli_nomb', 'cho_codi__cho_nomb', 'loc_orig__loc_nomb', 'loc_dest__loc_nomb']
    ordering = ['-via_fech', '-via_codi']
    filterset_fields = {
        'via_fech': ['exact', 'gte', 'lte'],
        'cam_codi': ['exact'], 'cho_codi': ['exact'], 'cli_codi': ['exact'],
        'gen_codi': ['exact'], 'tse_codi': ['exact'], 'rec_codi': ['exact'],
    }


class CobranzasViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Cobranzas.objects.select_related('fac_codi')
    serializer_class = CobranzasSerializer
    lookup_field_name = 'cob_codi'
    search_fields = ['fac_codi__fac_nume']
    ordering = ['-cob_fech']
    filterset_fields = {'cob_fech': ['exact', 'gte', 'lte'], 'fac_codi': ['exact']}


#----------------------------------------------------------GASTOS↓----------------------------------------------------------------------

class RubroCostoViewSet(BulkCreateMixin, BaseViewSet):
    queryset = RubroCosto.objects.all()
    serializer_class = RubroCostoSerializer
    lookup_field_name = 'rco_codi'
    search_fields = ['rco_nomb']
    ordering = ['rco_codi']


class GastosViewSet(BulkCreateMixin, BaseViewSet):
    queryset = Gastos.objects.select_related('rco_codi', 'cam_codi')
    serializer_class = GastosSerializer
    lookup_field_name = 'gas_codi'
    search_fields = ['gas_conc', 'cam_codi__cam_pate']
    ordering = ['-gas_fech']
    filterset_fields = {'gas_fech': ['exact', 'gte', 'lte'], 'rco_codi': ['exact'], 'cam_codi': ['exact']}


#--------------------------------------------------------IMPORTAR DATOS↓---------------------------------------------------------------

# En orden de dependencias: cada tabla se carga después de las que referencia.
MODELOS = {
    "general": (General, "gen_codi"),
    "parametros": (Parametros, "par_codi"),
    "provincias": (Provincia, "pci_codi"),
    "localidades": (Localidad, "loc_codi"),                # depende de Provincia
    "legajos_personal": (LegajoPersonal, "per_codi"),
    "choferes": (Choferes, "cho_codi"),                    # depende de LegajoPersonal
    "sueldos": (Sueldos, "sue_codi"),                      # depende de LegajoPersonal
    "clientes": (Clientes, "cli_codi"),
    "tipos_servicio": (TipoServicio, "tse_codi"),
    "tipos_cubierta": (TipoCubierta, "tcu_codi"),
    "modelos": (Modelo, "mod_codi"),
    "camiones": (Camiones, "cam_codi"),                    # depende de Modelo, TipoServicio, Choferes (los acoplados van primero)
    "recorridos": (Recorridos, "rec_codi"),                # depende de Camiones
    "facturas": (Facturas, "fac_codi"),                    # depende de Clientes, General
    "viajes": (Viajes, "via_codi"),                        # depende de Camiones, Choferes, Clientes, General, TipoServicio, Localidad, Recorridos, Facturas
    "cobranzas": (Cobranzas, "cob_codi"),                  # depende de Facturas
    "rubros_costo": (RubroCosto, "rco_codi"),
    "gastos": (Gastos, "gas_codi"),                        # depende de RubroCosto, Camiones
}


def importar(data):
    """Carga un dict {"tabla": [registros]} con upsert por la PK de cada modelo. Devuelve el resumen por tabla."""
    resultados = {}

    for key, (model, lookup) in MODELOS.items():

        items = data.get(key, [])
        if not items:
            continue

        resultados[key] = {
            "total": len(items),
            "ok": 0,
            "error": 0,
            "detalle": [],
        }

        for item in items:
            data_item = dict(item)
            try:
                with transaction.atomic():

                    # strings vacíos -> NULL
                    for k, v in list(data_item.items()):
                        if isinstance(v, str):
                            v = v.strip()
                            data_item[k] = v or None

                    # FK -> *_id
                    for field in model._meta.fields:
                        if field.is_relation and field.many_to_one and field.name in data_item:
                            data_item[f"{field.name}_id"] = data_item.pop(field.name)

                    lookup_value = data_item.pop(lookup, None)
                    if lookup_value is None:
                        resultados[key]["error"] += 1
                        resultados[key]["detalle"].append({"error": f"Falta campo {lookup}", "data": item})
                        continue

                    model.objects.update_or_create(**{lookup: lookup_value}, defaults=data_item)
                    resultados[key]["ok"] += 1

            except Exception as e:
                print(f"ERROR IMPORTANDO {key} ({model.__name__}): {item}")
                traceback.print_exc()
                resultados[key]["error"] += 1
                resultados[key]["detalle"].append({"error": str(e), "data": item})

    return resultados


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def importar_datos(request):
    """
    POST /api/importar_datos/
    Importa datos en bulk desde JSON.
    Body esperado: {"camiones": [...], "viajes": [...], "gastos": [...], ...}
    con una clave por cada modelo definido en MODELOS
    """

    if request.method == 'OPTIONS':
        return JsonResponse({'status': 'ok'})

    if not (settings.API_PUBLICA or clave_valida(request)
            or (request.user.is_authenticated and request.user.is_staff)):
        return JsonResponse(
            {'success': False, 'detail': 'Falta la clave de API (Authorization: Bearer <clave>).'},
            status=401,
        )

    try:
        data = json.loads(request.body)
    except Exception as e:
        return JsonResponse({'success': False, 'detail': f'JSON inválido: {str(e)}'}, status=400)

    try:
        return JsonResponse({"success": True, "resultados": importar(data)}, status=200)
    except Exception as e:
        print(traceback.format_exc())
        return JsonResponse({"success": False, "error": str(e)}, status=500)
