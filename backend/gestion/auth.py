import hmac

from django.conf import settings
from rest_framework import authentication, exceptions


class ApiKeyUser:
    """Usuario "virtual" para pedidos que se identifican con API_SYNC_KEY (dashboard, carga de datos)."""
    is_authenticated = True
    is_active = True
    is_staff = False
    is_superuser = False
    username = 'api-key'
    pk = None

    def __str__(self):
        return self.username


def clave_del_pedido(request):
    """Lee la clave de 'Authorization: Bearer <clave>' o de 'X-API-Key: <clave>'."""
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.lower().startswith('bearer '):
        return auth[7:].strip()
    return request.META.get('HTTP_X_API_KEY', '').strip()


def clave_valida(request):
    esperada = settings.API_SYNC_KEY
    recibida = clave_del_pedido(request)
    return bool(esperada and recibida) and hmac.compare_digest(recibida, esperada)


class ApiKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        if not clave_del_pedido(request):
            return None  # sin clave: probar con la sesión del admin
        if not clave_valida(request):
            raise exceptions.AuthenticationFailed('Clave de API inválida.')
        return ApiKeyUser(), None

    def authenticate_header(self, request):
        # Hace que DRF responda 401 (y no 403) cuando falta la clave
        return 'Bearer realm="api"'
