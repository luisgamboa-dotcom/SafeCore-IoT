"""Ingesta de lecturas, API en vivo y panel de datos."""
import json
import os
from uuid import UUID

import mysql.connector

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from config.sessionsConfig import SessionData, cookie as session_cookie, verificador
from models import readingsModel as lec_model
from models import devicesModel as dev_model
from models import zonesModel as zone_model
from models import installationsModel as inst_model
from models import alertsModel as alerts_model
from utils import batchStore, liveStore, nodeIps
from utils import gasConversion
from utils.commonUtils import userSessionContext, restrictedOrganization, \
    dashboardOrganization, organizationSerials
from utils.flashUtils import popFormFlash

templates = Jinja2Templates(directory="templates")

# Sin persistencia por defecto: solo en vivo. Configurar SAVE_READINGS=1 en .env para persistir.
SAVE_TO_DB = os.getenv("SAVE_READINGS") == "1"

# Editable: segundos que se acumulan las lecturas antes del envío del lote a la BD.
AGGREGATE_INTERVAL_S = 60

# Rangos de calidad sobre el VALOR CRUDO que llega del nodo (el gas llega en
# cuentas ADC 0-1023; la conversion a ppm se hace en la ingesta, ver abajo).
RANGOS = {"gas": (0, 1023), "temp": (-40.0, 80.0), "hum": (0.0, 100.0)}

batchStore.start(AGGREGATE_INTERVAL_S, lambda: SAVE_TO_DB)


class ReadingIn(BaseModel):
    tipo: Literal["gas", "temp", "hum"]
    valor_crudo: float


class IngestIn(BaseModel):
    device_serial: str = Field(min_length=1, max_length=100)
    device_id: Optional[str] = Field(default=None, max_length=50)
    fw: Optional[str] = None
    seq: int = Field(ge=0)
    uptime_ms: Optional[int] = None
    readings: List[ReadingIn] = Field(min_length=1, max_length=10)


def ingestReadings(request: Request, payload: IngestIn):
    # Ultima IP conocida del nodo (para abrir la PWA de config desde el panel).
    # Nunca interrumpe el ingest.
    try:
        ip_cliente = request.client.host if request.client else None
        nodeIps.recordar(payload.device_serial, ip_cliente)
    except Exception:
        pass

    # Log de diagnostico: valores crudos que reporta el nodo (1 linea/POST,
    # rotado: se conservan las ultimas 300 lineas ~50 min).
    try:
        _LOG = os.path.join("data", "ingest_debug.jsonl")
        lineas = []
        if os.path.exists(_LOG):
            with open(_LOG, "r", encoding="utf-8") as f:
                lineas = f.read().splitlines()[-299:]
        lineas.append(json.dumps(payload.model_dump()))
        with open(_LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")
    except Exception:
        pass

    calificadas = []
    dudosas = 0
    for r in payload.readings:
        lo, hi = RANGOS[r.tipo]
        calidad = "valida" if (lo <= float(r.valor_crudo) <= hi) else "dudosa"
        if calidad == "dudosa":
            dudosas += 1
        # Gas: se guarda y muestra en ppm (estimado via curva del datasheet);
        # el crudo ADC solo queda en el log de diagnostico.
        valor = (gasConversion.adc_a_ppm(r.valor_crudo) if r.tipo == "gas"
                 else float(r.valor_crudo))
        calificadas.append({"tipo": r.tipo,
                            "valor_crudo": float(r.valor_crudo),
                            "valor": valor,
                            "calidad": calidad})
    liveStore.push(payload.device_serial, payload.fw, payload.seq, calificadas)
    pendientes = batchStore.add(payload.device_serial, payload.fw, payload.seq, calificadas)

    # Metadatos del nodo: corren SIEMPRE (tambien en vivo-sin-guardar).
    # Tolerante a BD caida: si falla, el ingest sigue igual.
    dev = None
    bd_error = None
    try:
        dev = lec_model.matchDeviceBySerial(payload.device_serial, payload.device_id)
        # HU-014: un dispositivo dado de baja no refresca su estado ni firmware.
        if dev is not None and "conflicto" not in dev and "no_activo" not in dev:
            # El dispositivo que reporta está vivo: última comunicación AHORA (+ estado de vuelta
            # a online si estaba offline). No guarda lecturas, solo metadatos.
            lec_model.markDeviceAlive(dev["id_dispositivo"])
            # FW reportado por el nodo: persistir si difiere de la BD (PWA 3.0+)
            if payload.fw and payload.fw != dev.get("firmware_version"):
                lec_model.updateFirmwareVersion(dev["id_dispositivo"], payload.fw)
    except Exception as e:
        dev = None
        bd_error = f"DB no disponible, en vivo igual: {e}"

    if bd_error:
        bd_estado = "db-no-disponible"
    elif dev is None:
        bd_estado = "no-registrado"
    elif "conflicto" in dev:
        bd_estado = "conflicto"
    elif "no_activo" in dev:
        bd_estado = "no_activo"
    else:
        bd_estado = "sincronizado"

    # HU-014: la ingesta de un dispositivo desactivado se rechaza sin guardar
    # lecturas ni actualizar nada (tambien en modo en-vivo).
    if dev is not None and "no_activo" in dev:
        return JSONResponse(
            status_code=409,
            content={"ok": False, "error": "Dispositivo no activo"},
        )
    if not SAVE_TO_DB:
        return {"ok": True, "insertadas": 0, "persistidas": 0,
                "recibidas": len(calificadas), "dudosas": dudosas,
                "pendientes": pendientes, "errores": ([bd_error] if bd_error else []),
                "bd": bd_estado, "modo": "en-vivo-sin-guardar"}
    if dev is None:
        return JSONResponse(
            status_code=404,
            content={"ok": False,
                     "error": f"Dispositivo '{payload.device_serial}' no existe. "
                              "Crealo en dispositivos con su identificador único "
                              "(ver sql/seed_datos_test.sql)."},
        )
    if "conflicto" in dev:
        return JSONResponse(
            status_code=409,
            content={"ok": False,
                     "error": f"El nodo con serial '{payload.device_serial}' reporta "
                              f"identificador único distinto al registrado "
                              f"({dev['conflicto']} ≠ {dev['identificador_unico']}). "
                              "Revisa el DEVICE= del nodo o el registro del dispositivo."},
        )
    return {"ok": True, "acumuladas": len(calificadas), "recibidas": len(calificadas),
            "dudosas": dudosas, "pendientes": pendientes, "errores": [],
            "bd": bd_estado, "modo": "acumulando"}


def getLiveReadings(request: Request,
                    limit: int = 50,
                    id_sesion: UUID = Depends(session_cookie),
                    sesion: SessionData = Depends(verificador)):
    # Mismo alcance que el dashboard: cada usuario ve solo su organización.
    org = dashboardOrganization(sesion)
    lecturas = liveStore.get_latest(limit)
    if org is not None:
        seriales = organizationSerials(org)
        lecturas = [l for l in lecturas if l["codigo_serial"] in seriales]
    return {"ok": True, "modo": "en-vivo-sin-guardar",
            "lecturas": lecturas}


def getBatchView(request: Request,
                 id_sesion: UUID = Depends(session_cookie),
                 sesion: SessionData = Depends(verificador)):
    return {"ok": True, **batchStore.snapshot()}


def showLiveView(request: Request,
                 id_sesion: UUID = Depends(session_cookie),
                 sesion: SessionData = Depends(verificador)):
    org = dashboardOrganization(sesion)
    lecturas = liveStore.get_latest(50)
    if org is not None:
        seriales = organizationSerials(org)
        lecturas = [l for l in lecturas if l["codigo_serial"] in seriales]
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(
        request, "datos/live-view.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok,
         "lecturas": lecturas,
         "intervalo": batchStore.snapshot()["intervalo_s"],
         **userSessionContext(sesion)})


def getLatestReadings(request: Request,
                      limit: int = 50,
                      id_sesion: UUID = Depends(session_cookie),
                      sesion: SessionData = Depends(verificador)):
    org = dashboardOrganization(sesion)
    if SAVE_TO_DB:
        try:
            return {"ok": True, "lecturas": lec_model.getLatest(limit, org)}
        except Exception:
            pass
    return getLiveReadings(limit, sesion)


def getHistoricoReadings(request: Request,
                         limit: int = 150,
                         id_sesion: UUID = Depends(session_cookie),
                         sesion: SessionData = Depends(verificador)):
    org = dashboardOrganization(sesion)
    try:
        return {"ok": True, "modo": "bd",
                "lecturas": lec_model.getHistoricoPorMagnitud(limit, org)}
    except Exception as e:
        return {"ok": False, "modo": "bd-no-disponible", "lecturas": [],
                "error": str(e)}


def getZonaSeries(request: Request,
                  id_zona: int,
                  limite: int = 300,
                  id_sesion: UUID = Depends(session_cookie),
                  sesion: SessionData = Depends(verificador)):
    org = dashboardOrganization(sesion)
    if org is not None:
        zona = zone_model.getZoneById(id_zona)
        inst = inst_model.getInstallationById(zona["id_instalacion"]) if zona else None
        if inst is None or inst["id_organizacion"] != org:
            return JSONResponse(
                {"ok": False, "modo": "bd", "lecturas": [],
                 "error": "La zona no pertenece a tu organizacion."})
    try:
        return {"ok": True, "modo": "bd",
                "lecturas": lec_model.getSerieZona(id_zona, limite)}
    except Exception as e:
        return {"ok": False, "modo": "bd-no-disponible", "lecturas": [],
                "error": str(e)}


def showDataPage(request: Request,
                 id_sesion: UUID = Depends(session_cookie),
                 sesion: SessionData = Depends(verificador)):
    # Dashboard principal: cada usuario ve solo los dispositivos de su
    # organización (None = usuario sin organización -> panel global).
    org = dashboardOrganization(sesion)
    try:
        dispositivos = dev_model.getActiveDevices(org)
    except Exception:
        dispositivos = []
    try:
        alertas = alerts_model.getRecentAlerts(org, limite=8)
        alertas_abiertas = alerts_model.countActiveAlerts(org)
    except Exception:
        alertas = []
        alertas_abiertas = 0
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(
        request, "datos/index.html",
        {"request": request, "dispositivos": dispositivos,
         "alertas": alertas, "alertas_abiertas": alertas_abiertas,
         "org_alcance": org,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **userSessionContext(sesion)})


def showAlertasPage(request: Request,
                    id_sesion: UUID = Depends(session_cookie),
                    sesion: SessionData = Depends(verificador)):
    """Pagina de alertas: tarjetas con todas las alertas de la organizacion
    del usuario (None = global), expandibles con todo su detalle."""
    org = dashboardOrganization(sesion)
    try:
        alertas = alerts_model.getAlertasCompletas(org, limite=50)
    except Exception:
        alertas = []
    conteo = {}
    for a in alertas:
        conteo[a["severidad"]] = conteo.get(a["severidad"], 0) + 1
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(
        request, "datos/alertas.html",
        {"request": request, "alertas": alertas,
         "conteo_severidad": conteo, "org_alcance": org,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **userSessionContext(sesion)})


def showSensoresPage(request: Request,
                     id_sesion: UUID = Depends(session_cookie),
                     sesion: SessionData = Depends(verificador)):
    """Pagina de sensores: estado de los dispositivos activos de la
    organizacion del usuario (None = global)."""
    org = dashboardOrganization(sesion)
    try:
        dispositivos = dev_model.getActiveDevices(org)
    except Exception:
        dispositivos = []
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(
        request, "datos/sensores.html",
        {"request": request, "dispositivos": dispositivos,
         "org_alcance": org,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **userSessionContext(sesion)})


def showHistorialPage(request: Request,
                      id_sesion: UUID = Depends(session_cookie),
                      sesion: SessionData = Depends(verificador)):
    """Pagina de historial: grafico en vivo con semilla historica de la
    organizacion del usuario, con pestañas por magnitud y estadisticas."""
    flash_msg, _, flash_ok = popFormFlash(request)
    org = dashboardOrganization(sesion)
    return templates.TemplateResponse(
        request, "datos/historial.html",
        {"request": request, "org_alcance": org,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **userSessionContext(sesion)})


def nodeConfig(serial: str):
    """Config que consulta el nodo IoT (FW 3.0+) para saber si esta registrado."""
    dev = dev_model.getDeviceBySerial(serial)
    if dev is None:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "registrado": False,
                     "error": f"El nodo '{serial}' no esta registrado en la "
                              "base de datos. Crealo en dispositivos con ese "
                              "codigo serial."})
    return {"ok": True, "registrado": True,
            "codigo_serial": dev["codigo_serial"],
            "nombre": dev["nombre"],
            "estado": dev["estado"],
            "modelo": dev["nombre_modelo"],
            "zona": dev["zona"],
            "firmware_version": dev["firmware_version"],
            "identificador_unico": dev["identificador_unico"]}
