import sys
import os
import json
import requests
import csv
from datetime import datetime
from decimal import Decimal

# ============================================================
# CONFIG
# ============================================================
#Subida informacon .py adapatar con los campos de murray

BASE_URL = "http://127.0.0.1:8000/api"
# BASE_URL = "https://dashboard.ferreteradebandi.online/api/"

URL = f"{BASE_URL}/importar_datos/"

RUTA_TMP = "SubInfo.tmp"

SALIDA = "banderasubASR.tmp"

CHECKPOINT = "sync_status.json"

TIMEOUT = 300

TAM_LOTE = 500

HEADERS = {
    "Content-Type": "application/json; charset=utf-8"
}

# ============================================================
# GENERAR SALIDA
# ============================================================

def generar_salida(estado):

    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(str(estado))


# ============================================================
# CONVERTIR TIPOS
# ============================================================

def convertir(valor, tipo):

    if valor is None:
        return None

    valor = str(valor).strip()

    if valor == "":
        return ""

    try:

        if tipo == int:

            valor = valor.replace(",", ".")

            return int(float(valor))

        if tipo == bool:

            return valor.lower() in (
                "true",
                "1",
                "t",
                "s",
                "si",
                "y"
            )

        if tipo == str:
            # No tocar: un texto (documento, CUIT, telefono) no se
            # normaliza como numero aunque "parezca" uno, o se
            # corrompe (ej: "11501020" -> "1.150102E+7").
            return valor

        # Decimal: normalizar numeros con coma como separador
        valor = valor.replace(",", ".")

        try:
            numero = Decimal(valor)
            return str(numero.normalize())
        except Exception:
            pass

        return valor

    except Exception:

        return ""


# ============================================================
# LIMPIAR TEXTO
# ============================================================

def limpiar_texto(valor):

    if not isinstance(valor, str):
        return valor

    valor = valor.replace("\x00", "")
    valor = valor.replace("�", "")
    valor = valor.replace("\r", "")
    valor = valor.replace("\n", "")

    return valor.strip()


# ============================================================
# FECHAS
# ============================================================

def normalizar_fecha(valor):

    if valor is None:
        return None

    valor = str(valor).strip()

    if valor == "":
        return None

    # Casos como "/  /", "//", "/", " / / "
    if valor.replace("/", "").strip() == "":
        return None

    # El .tmp viene siempre en formato DD/MM/YY (origen FoxPro,
    # convencion argentina).
    try:
        fecha = datetime.strptime(valor, "%d/%m/%y")
        return fecha.strftime("%Y-%m-%d")
    except ValueError:
        pass

    return valor


# ============================================================
# ACCESO SEGURO A COLUMNAS
# ============================================================
# Igual que en SubInfo.py: si la fila no tiene esa posicion,
# se devuelve "" (no rompe el registro). Aplica convertir +
# limpiar_texto + normalizar_fecha en un solo lugar para que
# los leer_xxx() de abajo queden como una linea por campo.

def campo(row, idx, tipo=str, es_fecha=False):

    if idx >= len(row):
        return ""

    valor = convertir(row[idx], tipo)
    valor = limpiar_texto(valor)

    if es_fecha:
        valor = normalizar_fecha(valor)

    return valor


# ============================================================
# REPARAR COMILLAS EN ARTICULOS
# ============================================================
# El tipo de linea real en el .tmp es "arti" (ver DESPACHO /
# DESTINOS). Antes decia "arbi" y nunca se disparaba.

def reparar_linea_articulo(linea):

    if ',"arti",' not in linea:
        return linea

    pos = linea.find(',"arti",')

    if pos == -1:
        return linea

    partes = linea.split('"')

    if len(partes) < 8:
        return linea

    resultado = ""
    dentro_nombre = False
    contador = 0

    i = 0
    while i < len(linea):

        c = linea[i]

        if c == '"':

            contador += 1

            # inicio nombre
            if contador == 5:
                dentro_nombre = True
                resultado += c
                i += 1
                continue

            # fin nombre
            if dentro_nombre:

                siguiente = linea[i + 1:i + 3]

                # si viene coma despues -> fin campo real
                if siguiente == ',"':
                    dentro_nombre = False
                    resultado += c
                    i += 1
                    continue

                # si NO -> es pulgadas internas
                resultado += '""'
                i += 1
                continue

        resultado += c
        i += 1

    return resultado


# ============================================================
# PARSER CSV
# ============================================================

def parse_line(line):

    try:

        reader = csv.reader(
            [line],
            delimiter=',',
            quotechar='"',
            skipinitialspace=False
        )

        return next(reader)

    except Exception as e:

        print("===================================")
        print("ERROR PARSEANDO")
        print(line)
        print(e)

        return []


# ============================================================
# LECTORES POR TIPO DE LINEA
# ============================================================
# Cada funcion arma el registro leyendo columna por columna,
# en el mismo orden en que aparecen en el .tmp (row[0]=id interno,
# row[1]=tipo, row[2] en adelante son los datos del registro).
# El orden respeta gestion/models.py salvo que la muestra real
# del .tmp indique otro orden (loca, srub, pers, prov).

def leer_general(row):
    return {
        "gen_codi": campo(row, 2, int),
        "gen_nomb": campo(row, 3, str),
        "gen_cuit": campo(row, 4, str),
        "gen_dire": campo(row, 5, str),
        "gen_tele": campo(row, 6, str),
    }


def leer_zona(row):
    return {
        "zon_codi": campo(row, 2, int),
        "zon_nomb": campo(row, 3, str),
    }


def leer_canal_venta(row):
    return {
        "can_codi": campo(row, 2, int),
        "can_nomb": campo(row, 3, str),
    }


def leer_provincia(row):
    return {
        "pci_codi": campo(row, 2, int),
        "pci_nomb": campo(row, 3, str),
    }


def leer_condicion_iva(row):
    return {
        "civ_codi": campo(row, 2, int),
        "civ_nomb": campo(row, 3, str),
    }


def leer_legajo_personal(row):
    return {
        "per_codi": campo(row, 2, int),
        "per_nomb": campo(row, 3, str),
        "per_Ndoc": campo(row, 4, str),
        "Per_CUIL": campo(row, 5, str),
        "Per_domi": campo(row, 6, str),
        "Per_Celu": campo(row, 7, str),
        "Per_mail": campo(row, 8, str),
        "per_alta": campo(row, 9, str, es_fecha=True),
        "per_baja": campo(row, 10, str, es_fecha=True),
        "loc_codi": campo(row, 11, str),
    }


def leer_grupo_cliente(row):
    return {
        "grc_codi": campo(row, 2, int),
        "grc_nomb": campo(row, 3, str),
    }


def leer_comodin_cliente(row):
    return {
        "cli_ccom": campo(row, 2, int),
        "cli_ncom": campo(row, 3, str),
    }


def leer_localidad(row):
    return {
        "loc_codi": campo(row, 2, int),
        "pci_codi": campo(row, 3, int),
        "loc_nomb": campo(row, 4, str),
        "loc_cpos": campo(row, 5, int),
    }


def leer_rubro(row):
    return {
        "rub_codi": campo(row, 2, int),
        "rub_nomb": campo(row, 3, str),
    }


def leer_subrubro(row):
    return {
        "sru_codi": campo(row, 2, int),
        "rub_codi": campo(row, 3, int),
        "sru_nomb": campo(row, 4, str),
    }


def leer_submarca(row):
    return {
        "smar_codi": campo(row, 2, int),
        "smar_nomb": campo(row, 3, str),
    }


def leer_marca(row):
    return {
        "mar_codi": campo(row, 2, int),
        "mar_nomb": campo(row, 3, str),
    }


def leer_proveedor(row):
    # confirmar contra el sistema origen: en la muestra real
    # (linea "prov") la columna row[4] siempre vino en "0" y no se
    # corresponde con ningun campo del modelo Proveedor -> se ignora.
    # row[8] (vacio en la muestra) y las dos fechas row[9]/row[10]
    # tampoco existen en el modelo -> se ignoran.
    # row[12]/row[13] respetan el orden de declaracion del modelo
    # (loc_codi antes que civ_codi).
    return {
        "pro_codi": campo(row, 2, int),
        "Pro_nomb": campo(row, 3, str),
        "pro_Cuit": campo(row, 5, str),
        "pro_dire": campo(row, 6, str),
        "pro_celu": campo(row, 7, str),
        "pro_ibru": campo(row, 11, str),
        "loc_codi": campo(row, 12, int),
        "civ_codi": campo(row, 13, int),
    }


def leer_comodin_articulo(row):
    return {
        "art_ccom": campo(row, 2, int),
        "art_ncom": campo(row, 3, str),
    }


def leer_cliente(row):
    return {
        "cli_codi": campo(row, 2, int),
        "cli_nomb": campo(row, 3, str),
        "cli_ndoc": campo(row, 4, str),
        "cli_cuit": campo(row, 5, str),
        "cli_dire": campo(row, 6, str),
        "cli_celu": campo(row, 7, str),
        "cli_emai": campo(row, 8, str),
        "cli_alta": campo(row, 9, str, es_fecha=True),
        "cli_baja": campo(row, 10, str, es_fecha=True),
        # row[11] (justo despues de cli_baja) se ignora a proposito:
        "can_codi": campo(row, 12, int),
        "zon_codi": campo(row, 13, int),
        "grc_codi": campo(row, 14, int),
        "loc_codi": campo(row, 15, int),
        "civ_codi": campo(row, 16, int),
        "per_codi": campo(row, 17, int),
        "cli_ccom": campo(row, 18, int),
    }


def leer_articulo(row):
    return {
        "art_codi": campo(row, 2, int),
        "art_nomb": campo(row, 3, str),
        "art_medi": campo(row, 4, str),
        "art_umed": campo(row, 5, str),
        "art_uequ": campo(row, 6, str),
        "art_ucos": campo(row, 7, str),
        "art_tprec": campo(row, 8, str),
        "art_prec": campo(row, 9, int),
        "art_pnet": campo(row, 10, int),
        "art_pfin": campo(row, 11, int),
        "art_tiva": campo(row, 12, int),
        "art_iint": campo(row, 13, int),
        "art_habi": campo(row, 14, bool),
        "art_pesa": campo(row, 15, bool),
        "art_ccom": campo(row, 16, int),
        "pro_codi": campo(row, 17, int),
        "sru_codi": campo(row, 18, int),
        "mar_codi": campo(row, 19, int),
        "smar_codi": campo(row, 20, int),
    }


def leer_sucursal(row):
    return {
        "suc_codi": campo(row, 2, int),
        "suc_nomb": campo(row, 3, str),
    }


def leer_comodin_venta(row):
    return {
        "vta_ccom": campo(row, 2, int),
        "vta_ncom": campo(row, 3, str),
    }


def leer_venta(row):
    return {
        "vta_codi": campo(row, 2, int),
        "cli_codi": campo(row, 3, int),
        "vta_fech": campo(row, 4, str, es_fecha=True),
        "vta_cvta": campo(row, 5, str),
        "suc_codi": campo(row, 6, int),
        "gen_codi": campo(row, 7, int),
        "vta_ccom": campo(row, 8, int),
        "vta_itoR": campo(row, 9, Decimal),
        "vta_igra": campo(row, 10, Decimal),
        "vta_iexe": campo(row, 11, Decimal),
        "vta_iiva": campo(row, 12, Decimal),
        "vta_iiin": campo(row, 13, Decimal),
        "vta_ibts": campo(row, 14, Decimal),
        # "vta_canc": campo(row, 15, int), #por ahora comentado cantidad comprobante, agregado 21/8/26
    }


def leer_detalle_venta(row):
    # confirmado contra el .tmp real: entre vta_codi y art_codi vienen
    # cli_codi(3), vta_fech(4), vta_cvta(5), suc_codi(6) -> se ignoran,
    # ya estan disponibles a traves de la FK vta_codi -> Ventas.
    return {
        "vta_codi": campo(row, 2, int),
        "art_codi": campo(row, 7, int),
        "dvt_iOri": campo(row, 8, Decimal),
        "dvt_iuni": campo(row, 9, Decimal),
        "dvt_itot": campo(row, 10, Decimal),
        "dvt_cost": campo(row, 11, Decimal),
        "dvt_iiva": campo(row, 12, Decimal),
        "dvt_igra": campo(row, 13, Decimal),
        "dvt_iexe": campo(row, 14, Decimal),
        "dvt_iint": campo(row, 15, Decimal),
        "dvt_caPi": campo(row, 16, Decimal),
        "dvt_cant": campo(row, 17, Decimal),
    }


def leer_cobranza(row):
    return {
        "cob_codi": campo(row, 2, int),
        "cob_fech": campo(row, 3, str, es_fecha=True),
        "cob_itot": campo(row, 4, Decimal),
        "cli_codi": campo(row, 5, int),
        "suc_codi": campo(row, 6, int),
    }


# ============================================================
# DESPACHO TIPO -> (LECTOR, DESTINO JSON)
# ============================================================
# El destino debe coincidir con las claves de MODELOS en
# gestion/views.py (importar_datos), y se listan en orden de
# dependencia para que el envio por lotes respete las FK.

DESPACHO = {
    "gene": (leer_general, "general"),
    "zona": (leer_zona, "zonas"),
    "cana": (leer_canal_venta, "canales_venta"),
    "pcia": (leer_provincia, "provincias"),
    "civa": (leer_condicion_iva, "condiciones_iva"),
    "pers": (leer_legajo_personal, "legajos_personal"),
    "grcl": (leer_grupo_cliente, "grupos_cliente"),
    "comc": (leer_comodin_cliente, "comodines_cliente"),
    "loca": (leer_localidad, "localidades"),
    "rubr": (leer_rubro, "rubros"),
    "smar": (leer_submarca, "submarcas"),
    "marc": (leer_marca, "marcas"),
    "sucu": (leer_sucursal, "sucursales"),
    "comv": (leer_comodin_venta, "comodines_venta"),
    "coma": (leer_comodin_articulo, "comodines_articulo"),
    "clie": (leer_cliente, "clientes"),
    "srub": (leer_subrubro, "subrubros"),
    "prov": (leer_proveedor, "proveedores"),
    "arti": (leer_articulo, "articulos"),
    "vtas": (leer_venta, "ventas"),
    "dvta": (leer_detalle_venta, "detalles_venta"),
    "cob": (leer_cobranza, "cobranzas"),
}

DESTINOS = {tipo: destino for tipo, (_, destino) in DESPACHO.items()}


# ============================================================
# LEER TMP
# ============================================================

def leer_tmp(ruta):

    data_final = {destino: [] for destino in DESTINOS.values()}

    with open(ruta, "r", encoding="utf-8", errors="ignore") as f:

        for numero_linea, line in enumerate(f, start=1):

            line = line.strip()

            if not line:
                continue

            line = reparar_linea_articulo(line)

            row = parse_line(line)

            if len(row) < 3:
                continue

            tipo = row[1].lower()

            despacho = DESPACHO.get(tipo)

            if despacho is None:
                continue

            lector, destino = despacho

            registro = lector(row)

            data_final[destino].append(registro)

    return data_final


# ============================================================
# CHECKPOINTS
# ============================================================

def cargar_checkpoint():

    if not os.path.exists(CHECKPOINT):
        return {}

    try:

        with open(CHECKPOINT, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {}


def guardar_checkpoint(data):

    with open(CHECKPOINT, "w", encoding="utf-8") as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# ENVIAR API
# ============================================================

def enviar_api(tabla, registros):

    try:

        payload = {
            tabla: registros
        }

        r = requests.post(
            URL,
            headers=HEADERS,
            json=payload,
            timeout=TIMEOUT
        )

        print("===================================")
        print("TABLA:", tabla)
        print("STATUS:", r.status_code)

        try:

            respuesta = r.json()

            print(json.dumps(
                respuesta,
                indent=4,
                ensure_ascii=False
            ))

        except Exception:

            print(r.text)

        return r.status_code in (200, 201)

    except Exception as e:

        print("ERROR REQUEST:", e)

        return False


# ============================================================
# ENVIAR LOTES
# ============================================================

def enviar_por_lotes(tabla, registros, checkpoint):

    total = len(registros)

    if total == 0:
        return True

    inicio = checkpoint.get(tabla, 0)

    print("===================================")
    print(f"ENVIANDO {tabla.upper()}")
    print(f"TOTAL REGISTROS: {total}")
    print(f"REANUDANDO DESDE: {inicio}")

    for i in range(inicio, total, TAM_LOTE):

        lote = registros[i:i + TAM_LOTE]

        print("-----------------------------------")
        print(f"LOTE {i} A {i + len(lote)}")

        ok = enviar_api(tabla, lote)

        if not ok:
            return False

        checkpoint[tabla] = i + len(lote)

        guardar_checkpoint(checkpoint)

        print(f"CHECKPOINT {tabla}: {checkpoint[tabla]}")

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    data = leer_tmp(RUTA_TMP)

    checkpoint = cargar_checkpoint()

    for tabla, registros in data.items():

        if not registros:
            continue

        total = len(registros)

        actual = checkpoint.get(tabla, 0)

        if actual >= total:

            print(f"{tabla} YA SINCRONIZADA")
            continue

        ok = enviar_por_lotes(
            tabla,
            registros,
            checkpoint
        )

        if not ok:

            print(f"ERROR EN {tabla}")

            generar_salida(0)

            sys.exit(0)

    print("===================================")
    print("SINCRONIZACION COMPLETA")
    print("===================================")

    if os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)

    generar_salida(1)

    sys.exit(0)


if __name__ == "__main__":
    main()