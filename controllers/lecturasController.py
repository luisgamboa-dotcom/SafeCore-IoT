"""Controlador de lecturas: ingesta del dispositivo y vistas de datos."""
import os
from uuid import UUID

import mysql.connector

from fastapi import Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from config.sessionsConfig import (
    SessionData,
    cookie as session_cookie,
    verificador,
)
from models import lecturasModel as lec_model
from models import dispositivosModel as dev_model
from models import usersModel as user_model
from utils import liveStore
from utils.flashUtils import popFormFlash

templates = Jinja2Templates(directory="templates")

# Requisito: NO guardar por defecto. Solo memoria (liveStore).
# Para volver a persistir en MySQL: SAVE_READINGS=1 en .env.
SAVE_TO_DB = os.getenv("SAVE_READINGS", "0") == "1"

# Rangos de aceptacion del ADC crudo y DHT22. Fuera de rango -> 'dudosa'.
RANGOS = {"gas": (0, 1023), "temp": (-40.0, 80.0), "hum": (0.0, 100.0)}


class ReadingIn(BaseModel):
    tipo: Literal["gas", "temp", "hum"]
    valor_crudo: float


class IngestIn(BaseModel):
    device_serial: str = Field(min_length=1, max_length=100)
    fw: Optional[str] = None
    seq: int = Field(ge=0)
    uptime_ms: Optional[int] = None
    readings: List[ReadingIn] = Field(min_length=1, max_length=10)


def ingestReadings(payload: IngestIn):
    """Ingesta en vivo: califica y publica en memoria (persiste solo con SAVE_READINGS=1)."""
    calificadas = []
    dudosas = 0
    for r in payload.readings:
        lo, hi = RANGOS[r.tipo]
        calidad = "valida" if (lo <= float(r.valor_crudo) <= hi) else "dudosa"
        if calidad == "dudosa":
            dudosas += 1
        calificadas.append({"tipo": r.tipo,
                            "valor_crudo": float(r.valor_crudo),
                            "calidad": calidad})
    liveStore.push(payload.device_serial, payload.fw, payload.seq, calificadas)

    if not SAVE_TO_DB:
        return {"ok": True, "insertadas": 0, "persistidas": 0,
                "recibidas": len(calificadas), "dudosas": dudosas,
                "errores": [], "modo": "en-vivo-sin-guardar"}

    # Persistencia optativa (SAVE_READINGS=1). Si la DB falla, igual se
    # acepta el paquete en vivo y se informa el error sin 500.
    try:
        dev = lec_model.getDeviceBySerial(payload.device_serial)
    except Exception as e:
        return {"ok": True, "insertadas": 0, "persistidas": 0,
                "recibidas": len(calificadas), "dudosas": dudosas,
                "errores": [f"DB no disponible, solo en vivo: {e}"],
                "modo": "en-vivo-sin-guardar"}
    if dev is None:
        return JSONResponse(
            status_code=404,
            content={"ok": False,
                     "error": f"Dispositivo '{payload.device_serial}' no existe. "
                              "Createlo en dispositivos (ver sql/seed_datos_test.sql)."},
        )
    insertadas, errores = 0, []
    try:
        for r in calificadas:
            spec = lec_model.MAGNITUDES[r["tipo"]]
            id_mag = lec_model.ensureMagnitude(spec["nombre"], spec["unidad"], spec["simbolo"])
            id_sens = lec_model.ensureSensorForMagnitude(dev["id_dispositivo"], id_mag)
            try:
                lec_model.insertReading(r["valor_crudo"], r["calidad"], id_sens, id_mag)
            except mysql.connector.Error as e:
                if e.errno == 1452:
                    errores.append(f"FK inexistente para tipo '{r['tipo']}'")
                    continue
                if "trg_lecturas_validar_magnitud" in (e.msg or ""):
                    errores.append(f"Sensor sin magnitud '{r['tipo']}' permitida")
                    continue
                raise
            insertadas += 1
        if insertadas:
            lec_model.touchDevice(dev["id_dispositivo"])
    except mysql.connector.Error as e:
        return {"ok": True, "insertadas": insertadas, "persistidas": insertadas,
                "recibidas": len(calificadas), "dudosas": dudosas,
                "errores": errores + [f"DB: {e.msg}"], "modo": "en-vivo"}
    return {"ok": True, "insertadas": insertadas, "persistidas": insertadas,
            "recibidas": len(calificadas), "duplicadas": 0,
            "dudosas": dudosas, "errores": errores, "modo": "persistente"}


def getLiveReadings(limit: int = 50):
    """Fuente del dashboard en tiempo real: solo memoria, sin DB."""
    return {"ok": True, "modo": "en-vivo-sin-guardar",
            "lecturas": liveStore.get_latest(limit)}


def getLatestReadings(limit: int = 50):
    # Compat: si hay persistencia activa intenta DB, si no, memoria.
    if SAVE_TO_DB:
        try:
            return {"ok": True, "lecturas": lec_model.getLatest(limit)}
        except Exception:
            pass
    return getLiveReadings(limit)


def showDataPage(request: Request,
                 id_sesion: UUID = Depends(session_cookie),
                 sesion: SessionData = Depends(verificador)):
    # Dashboard principal (privado: exige sesión): solo memoria, funciona sin MySQL.
    lecturas = liveStore.get_latest(50)
    flash_msg, _, flash_ok = popFormFlash(request)
    roles = user_model.getUserRoles(sesion.id_usuario)
    user = user_model.getUserById(sesion.id_usuario)
    iniciales = user["nombre"][0] + (user["apellido"][0] if user and user["apellido"] else "") if user else ""
    try:
        dispositivos = dev_model.getActiveDevices()
    except Exception:
        dispositivos = []
    return templates.TemplateResponse(
        request, "datos/index.html",
        {"request": request, "lecturas": lecturas, "dispositivos": dispositivos,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         "is_admin": "Administrador" in roles,
         "iniciales": iniciales, "id_usuario": sesion.id_usuario})


def showDeviceDetail(request: Request,
                     id_dispositivo: int,
                     id_sesion: UUID = Depends(session_cookie),
                     sesion: SessionData = Depends(verificador)):
    # Detalle de un dispositivo (privado): ficha completa desde MySQL.
    dev = dev_model.getDeviceDetail(id_dispositivo)
    if dev is None:
        return RedirectResponse("/dashboard", status_code=303)
    roles = user_model.getUserRoles(sesion.id_usuario)
    user = user_model.getUserById(sesion.id_usuario)
    iniciales = user["nombre"][0] + (user["apellido"][0] if user and user["apellido"] else "") if user else ""
    return templates.TemplateResponse(
        request, "datos/dispositivo.html",
        {"request": request, "dev": dev,
         "is_admin": "Administrador" in roles,
         "iniciales": iniciales, "id_usuario": sesion.id_usuario})

