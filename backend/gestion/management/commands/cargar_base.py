from datetime import date

from django.core.management.base import BaseCommand

from gestion.formulas import RUBROS_BASE
from gestion.models import Parametros, RubroCosto, TipoCubierta, TipoServicio

SERVICIOS_BASE = ['Carretón', 'Bitren', 'Batea cereal', 'Camilla', 'Servicio de grúa']


class Command(BaseCommand):
    help = 'Crea las tablas fijas: los 12 rubros de costo del tablero, los parámetros del Excel y los tipos de servicio.'

    def handle(self, *args, **options):
        for codi, nomb, vari, mens in RUBROS_BASE:
            RubroCosto.objects.update_or_create(
                rco_codi=codi, defaults={'rco_nomb': nomb, 'rco_vari': vari, 'rco_mens': mens},
            )

        # Valores por defecto del modelo = los de la PLANILLA COSTO MAYO
        Parametros.objects.get_or_create(par_codi=1, defaults={
            'par_desd': date(2000, 1, 1),
            'par_scar': 336842,   # Costos por dominio!P = 336.842 ÷ 12
            'par_dola': 1230,     # Costos variables!C16
        })

        # Costos variables!C19:F21 (tabla CUB)
        for codi, nomb, medi, prec, kdur in [
            (1, 'LINEAL', '295/80/22,5', 415303, 135700),
            (2, 'TACO', '295/80/22,5 dr400', 499201, 179300),
            (3, 'CARRETON', '275/70 fate sr260', 412222, 125000),
        ]:
            TipoCubierta.objects.get_or_create(tcu_codi=codi, defaults={'tcu_nomb': nomb, 'tcu_prec': prec, 'tcu_kdur': kdur})

        for i, nomb in enumerate(SERVICIOS_BASE, start=1):
            if not TipoServicio.objects.filter(tse_nomb=nomb).exists():
                TipoServicio.objects.update_or_create(tse_codi=i, defaults={'tse_nomb': nomb})

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {RubroCosto.objects.count()} rubros de costo, {Parametros.objects.count()} parámetros, '
            f'{TipoServicio.objects.count()} tipos de servicio, {TipoCubierta.objects.count()} tipos de cubierta.'
        ))
