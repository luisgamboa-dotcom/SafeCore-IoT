import json
import os
from uuid import UUID

import mysql.connector

from fastapi import Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from config.sessionsConfig import SessionData, cookie as session_cookie, verificador
from utils.commonUtils import (userSessionContext, dashboardOrganization,
                               esUsuarioPremium)
from models import readingsModel as lec_model
from models import devicesModel as dev_model
from models import zonesModel as zone_model
from models import installationsModel as inst_model
from models import alertsModel as alerts_model
from models import mantenimientosModel as mant_model
from models.auditoriaModel import registrarAuditoria as registrarAuditoria
from utils import batchStore, liveStore, nodeIps
from utils import gasConversion
from utils.commonUtils import userSessionContext, restrictedOrganization, \
    dashboardOrganization, organizationSerials
from utils.flashUtils import popFormFlash, flashForm

templates = Jinja2Templates(directory="templates")


SAVE_TO_DB = os.getenv("SAVE_READINGS") == "1"


AGGREGATE_INTERVAL_S = 60



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


    try:
        ip_cliente = request.client.host if request.client else None
        nodeIps.recordar(payload.device_serial, ip_cliente)
    except Exception:
        pass



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


        valor = (gasConversion.adc_a_ppm(r.valor_crudo) if r.tipo == "gas"
                 else float(r.valor_crudo))
        calificadas.append({"tipo": r.tipo,
                            "valor_crudo": float(r.valor_crudo),
                            "valor": valor,
                            "calidad": calidad})
    liveStore.push(payload.device_serial, payload.fw, payload.seq, calificadas)
    pendientes = batchStore.add(payload.device_serial, payload.fw, payload.seq, calificadas)



    dev = None
    bd_error = None
    try:
        dev = lec_model.matchDeviceBySerial(payload.device_serial, payload.device_id)

        if dev is not None and "conflicto" not in dev and "no_activo" not in dev:


            lec_model.markDeviceAlive(dev["id_dispositivo"])

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
                    agrupado: bool = False,
                    id_sesion: UUID = Depends(session_cookie),
                    sesion: SessionData = Depends(verificador)):



    org = dashboardOrganization(sesion)
    lecturas = (liveStore.get_latest_por_magnitud(limit) if agrupado
                else liveStore.get_latest(limit))
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
    serial = request.query_params.get("serial") or None
    horas_q = request.query_params.get("horas", "")
    horas = int(horas_q) if horas_q.isdigit() and int(horas_q) in (0, 1, 24, 168, 720) else None
    try:
        return {"ok": True, "modo": "bd",
                "lecturas": lec_model.getHistoricoPorMagnitud(limit, org,
                                                              serial=serial, horas=horas)}
    except Exception as e:
        return {"ok": False, "modo": "bd-no-disponible", "lecturas": [],
                "error": str(e)}


def _horasValidas(valor, defecto=1):
    try:
        horas = int(valor)
    except (TypeError, ValueError):
        return defecto
    return horas if horas in (0, 1, 24, 168, 720) else defecto


def _serieVacia(magnitud):
    return {"ok": True, "modo": "bd", "magnitud": magnitud, "bucket_s": 300,
            "desde": None, "hasta": None,
            "stats": {"max": None, "min": None, "prom": None, "muestras": 0},
            "serie": []}


def getHistoricoSerie(request: Request,
                      serial: str = "",
                      horas: str = "1",
                      magnitud: str = "gas",
                      id_sesion: UUID = Depends(session_cookie),
                      sesion: SessionData = Depends(verificador)):
    org = dashboardOrganization(sesion)
    mag = magnitud if magnitud in lec_model.MAGNITUDES else "gas"
    serial = (serial or "").strip()
    if not serial:
        return _serieVacia(mag)
    try:
        return lec_model.getSerieDispositivo(serial, _horasValidas(horas), mag, org)
    except Exception as e:
        return {"ok": False, "modo": "bd-no-disponible", "serie": [],
                "error": str(e)}


def getHistoricoOrganizacion(request: Request,
                             horas: str = "1",
                             magnitud: str = "gas",
                             id_sesion: UUID = Depends(session_cookie),
                             sesion: SessionData = Depends(verificador)):
    org = dashboardOrganization(sesion)
    mag = magnitud if magnitud in lec_model.MAGNITUDES else "gas"
    try:
        return lec_model.getSerieOrganizacion(_horasValidas(horas), mag, org)
    except Exception as e:
        return {"ok": False, "modo": "bd-no-disponible", "serie": [],
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

    try:
        mant_pendientes = mant_model.getPendientesByResponsable(sesion.id_usuario)
    except Exception:
        mant_pendientes = []
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(
        request, "datos/index.html",
        {"request": request, "dispositivos": dispositivos,
         "alertas": alertas, "alertas_abiertas": alertas_abiertas,
         "mant_pendientes": mant_pendientes,
         "org_alcance": org, "sin_organizacion": org == -1,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **userSessionContext(sesion)})


def showAlertasPage(request: Request,
                    id_sesion: UUID = Depends(session_cookie),
                    sesion: SessionData = Depends(verificador)):
    params_q = request.query_params
    org = dashboardOrganization(sesion)
    premium_bloqueado = not esUsuarioPremium(sesion)
    estado = params_q.get("estado", "")
    if estado not in ("activas", "resueltas"):
        estado = None
    q = (params_q.get("q") or "").strip() or None

    def _id(nombre):
        valor = params_q.get(nombre, "")
        return int(valor) if valor.isdigit() else None

    severidad = params_q.get("severidad", "")
    if severidad not in ("critica", "alta", "media", "baja"):
        severidad = None
    fecha = params_q.get("fecha", "")
    if fecha not in ("hoy", "7d", "30d"):
        fecha = None
    filtros = {"q": q, "id_dispositivo": _id("dispositivo"),
               "id_zona": _id("zona"), "severidad": severidad, "fecha": fecha}
    alertas = []
    conteo_grupos = {"todas": 0, "activas": 0, "resueltas": 0}
    dispositivos_filtro = []
    zonas_filtro = []
    if not premium_bloqueado:
        # Plan gratuito: la seccion es Funcion Premium; sin datos reales.
        try:
            alertas = alerts_model.getAlertasCompletas(
                org, limite=50, estado=estado, **filtros)
            conteo_grupos = alerts_model.countAlertsByGroup(org)
        except Exception:
            alertas = []
            conteo_grupos = {"todas": 0, "activas": 0, "resueltas": 0}

        try:
            dispositivos_filtro = dev_model.getActiveDevices(org)
        except Exception:
            dispositivos_filtro = []
        try:
            zonas_filtro = zone_model.getZonasOrganizacion(org)
        except Exception:
            zonas_filtro = []
    conteo = {}
    for a in alertas:
        conteo[a["severidad"]] = conteo.get(a["severidad"], 0) + 1
    hay_filtros = any(filtros.values()) or estado is not None
    n_filtros = (sum(1 for v in filtros.values() if v)
                 + (1 if estado is not None else 0))
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(
        request, "datos/alertas.html",
        {"request": request, "alertas": alertas,
         "conteo_severidad": conteo, "org_alcance": org,
         "sin_organizacion": org == -1,
         "premium_bloqueado": premium_bloqueado,
         "estado_actual": estado, "conteo_grupos": conteo_grupos,
         **filtros,
         "dispositivos_filtro": dispositivos_filtro,
         "zonas_filtro": zonas_filtro,
         "hay_filtros": hay_filtros, "n_filtros": n_filtros,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **userSessionContext(sesion)})


def showSensoresPage(request: Request,
                     id_sesion: UUID = Depends(session_cookie),
                     sesion: SessionData = Depends(verificador)):
    org = dashboardOrganization(sesion)
    try:
        dispositivos = dev_model.getActiveDevices(org)
    except Exception:
        dispositivos = []

    try:
        from models import rulesModel
        umbrales = rulesModel.getActiveThresholdsByOrganization(org)
    except Exception:
        umbrales = {}
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(
        request, "datos/sensores.html",
        {"request": request, "dispositivos": dispositivos,
         "umbrales": umbrales,
         "org_alcance": org, "sin_organizacion": org == -1,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **userSessionContext(sesion)})


def showHistorialPage(request: Request,
                      id_sesion: UUID = Depends(session_cookie),
                      sesion: SessionData = Depends(verificador)):
    flash_msg, _, flash_ok = popFormFlash(request)
    org = dashboardOrganization(sesion)
    horas = request.query_params.get("horas", "1")
    try:
        from models import rulesModel
        umbrales = rulesModel.getActiveThresholdsByOrganization(org)
    except Exception:
        umbrales = {}
    return templates.TemplateResponse(
        request, "datos/historial.html",
        {"request": request, "org_alcance": org,
         "horas_export": horas if horas in ("1", "24", "168", "720", "0") else "1",
         "umbrales": umbrales,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **userSessionContext(sesion)})


def reconocerAlerta(request: Request,
                    id_alerta: int,
                    id_sesion: UUID = Depends(session_cookie),
                    sesion: SessionData = Depends(verificador)):
    if not esUsuarioPremium(sesion):
        flashForm(request, "Las alertas son parte del plan Premium. "
                           "Mejora tu plan para usarlas.")
        return RedirectResponse("/dashboard/alertas", status_code=303)
    alerta = alerts_model.getAlerta(id_alerta)
    org = dashboardOrganization(sesion)
    if (alerta is None or org == -1
            or (org is not None and alerta["id_organizacion"] != org)):
        flashForm(request, "La alerta no existe o no pertenece a tu organización.")
        return RedirectResponse("/dashboard/alertas", status_code=303)
    if alerta["estado"] == "resuelta":
        flashForm(request, "La alerta ya está resuelta: no se puede reconocer.")
        return RedirectResponse("/dashboard/alertas", status_code=303)
    ok = alerts_model.reconocerAlerta(id_alerta, sesion.id_usuario)
    if not ok:

        flashForm(request, "La alerta ya está reconocida.")
        return RedirectResponse("/dashboard/alertas", status_code=303)
    registrarAuditoria(sesion.id_usuario, "alerta", id_alerta, "reconocer",
                       "estado: pendiente", "estado: reconocida")
    flashForm(request, "Alerta reconocida correctamente.", ok=True)
    return RedirectResponse("/dashboard/alertas", status_code=303)


async def resolverAlerta(request: Request,
                         id_alerta: int,
                         id_sesion: UUID = Depends(session_cookie),
                         sesion: SessionData = Depends(verificador),
                         comentario: str = Form("")):
    if not esUsuarioPremium(sesion):
        flashForm(request, "Las alertas son parte del plan Premium. "
                           "Mejora tu plan para usarlas.")
        return RedirectResponse("/dashboard/alertas", status_code=303)
    alerta = alerts_model.getAlerta(id_alerta)
    org = dashboardOrganization(sesion)
    if (alerta is None or org == -1
            or (org is not None and alerta["id_organizacion"] != org)):
        flashForm(request, "La alerta no existe o no pertenece a tu organización.")
        return RedirectResponse("/dashboard/alertas", status_code=303)
    if alerta["estado"] == "pendiente":
        flashForm(request, "Debes reconocer la alerta antes de poder resolverla.")
        return RedirectResponse("/dashboard/alertas", status_code=303)
    if alerta["estado"] == "resuelta":
        flashForm(request, "La alerta ya está resuelta.")
        return RedirectResponse("/dashboard/alertas", status_code=303)
    texto = (comentario or "").strip()
    if not texto:
        flashForm(request, "El comentario de resolución es obligatorio.")
        return RedirectResponse("/dashboard/alertas", status_code=303)
    ok = alerts_model.resolverAlerta(id_alerta, sesion.id_usuario, texto)
    if not ok:

        flashForm(request, "La alerta ya está resuelta.")
        return RedirectResponse("/dashboard/alertas", status_code=303)
    registrarAuditoria(sesion.id_usuario, "alerta", id_alerta, "resolver",
                       "estado: reconocida",
                       f"estado: resuelta, comentario: {texto}")
    flashForm(request, "Alerta resuelta correctamente.", ok=True)
    return RedirectResponse("/dashboard/alertas", status_code=303)


def getAlertasActivasApi(request: Request,
                         id_sesion: UUID = Depends(session_cookie),
                         sesion: SessionData = Depends(verificador)):
    # Plan gratuito: sin pop-up de alertas (Funcion Premium).
    if not esUsuarioPremium(sesion):
        return JSONResponse({"ok": True, "alertas": []})
    org = dashboardOrganization(sesion)
    try:
        alertas = alerts_model.getAlertasActivas(org, limite=20)
    except Exception:
        alertas = []
    return JSONResponse(
        {"ok": True,
         "alertas": [{"id_alerta": a["id_alerta"],
                      "mensaje": a["mensaje_corto"],
                      "severidad": a["severidad"],
                      "estado": a["estado"],
                      "dispositivo": a["dispositivo"],
                      "codigo_serial": a["codigo_serial"],
                      "valor": str(a["valor_origen"]),
                      "unidad": a["unidad"] or "",
                      "fecha": a["fecha_inicio"].strftime("%d-%m-%Y %H:%M")
                      if a["fecha_inicio"] else ""}
                     for a in alertas]})


def nodeConfig(serial: str):
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
