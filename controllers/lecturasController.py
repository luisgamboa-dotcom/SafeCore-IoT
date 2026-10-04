"""
    Controlador de lecturas (MVC: Controller).
    Ingesta del dispositivo y vistas de datos. Sin SQL directo salvo
    el manejo de errores MySQL; las consultas viven en models/lecturasModel.py.
    Las rutas que apuntan a estas funciones viven en routers/lecturasRoutes.py.
"""

# controllers/lecturasController.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Optional
import mysql.connector

from models import lecturasModel as lec_model

templates = Jinja2Templates(directory="templates")

# Rangos de aceptacion del ADC crudo y DHT22. Fuera de rango -> 'dudosa'.
RANGOS = {"gas": (0, 1023), "temp": (-40.0, 80.0), "hum": (0.0, 100.0)}


class ReadingIn(BaseModel):
    tipo: str = Field(pattern="^(gas|temp|hum)$")
    valor_crudo: float


class IngestIn(BaseModel):
    device_serial: str = Field(min_length=1, max_length=100)
    fw: Optional[str] = None
    seq: int = Field(ge=0)
    uptime_ms: Optional[int] = None
    readings: List[ReadingIn] = Field(min_length=1, max_length=10)


def ingestReadings(payload: IngestIn):
    dev = lec_model.getDeviceBySerial(payload.device_serial)
    if dev is None:
        return JSONResponse(
            status_code=404,
            content={"ok": False,
                     "error": f"Dispositivo '{payload.device_serial}' no existe. "
                              "Createlo en dispositivos (ver sql/seed_datos_test.sql)."},
        )
    insertadas, dudosas, errores = 0, 0, []
    try:
        for r in payload.readings:
            spec = lec_model.MAGNITUDES[r.tipo]
            id_mag = lec_model.ensureMagnitude(spec["nombre"], spec["unidad"], spec["simbolo"])
            id_sens = lec_model.ensureSensorForMagnitude(dev["id_dispositivo"], id_mag)
            lo, hi = RANGOS[r.tipo]
            calidad = "valida" if (lo <= float(r.valor_crudo) <= hi) else "dudosa"
            if calidad == "dudosa":
                dudosas += 1
            try:
                lec_model.insertReading(
                    float(r.valor_crudo), calidad, id_sens, id_mag)
            except mysql.connector.Error as e:
                if e.errno == 1452:
                    errores.append(f"FK inexistente para tipo '{r.tipo}'")
                    continue
                if "trg_lecturas_validar_magnitud" in (e.msg or ""):
                    errores.append(f"Sensor sin magnitud '{r.tipo}' permitida")
                    continue
                raise
            insertadas += 1
        if insertadas:
            lec_model.touchDevice(dev["id_dispositivo"])
    except mysql.connector.Error as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": f"DB: {e.msg}"})
    return {"ok": True, "insertadas": insertadas, "duplicadas": 0,
            "dudosas": dudosas, "errores": errores}


def getLatestReadings(limit: int = 50):
    return {"ok": True, "lecturas": lec_model.getLatest(limit)}


def showDataPage(request: Request):
    # Vista de testeo: a proposito sin sesion ni diseno, solo tabla cruda.
    return templates.TemplateResponse(
        request, "datos/index.html",
        {"request": request, "lecturas": lec_model.getLatest(50)})
