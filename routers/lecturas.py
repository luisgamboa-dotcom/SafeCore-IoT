from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Optional
import mysql.connector

from models import lecturas as lec_model

router = APIRouter()
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


@router.post("/api/ingest")
def ingest(payload: IngestIn):
    dev = lec_model.get_dispositivo_por_serial(payload.device_serial)
    if dev is None:
        return JSONResponse(
            status_code=404,
            content={"ok": False,
                     "error": f"Dispositivo '{payload.device_serial}' no existe. "
                              "Createlo en dispositivos (ver sql/seed_datos_test.sql)."},
        )
    insertadas, duplicadas, dudosas, errores = 0, 0, 0, []
    try:
        for r in payload.readings:
            spec = lec_model.MAGNITUDES[r.tipo]
            id_mag = lec_model.ensure_magnitud(spec["nombre"], spec["unidad"], spec["simbolo"])
            id_sens = lec_model.ensure_sensor_para_magnitud(dev["id_dispositivo"], id_mag)
            lo, hi = RANGOS[r.tipo]
            calidad = "valida" if (lo <= float(r.valor_crudo) <= hi) else "dudosa"
            if calidad == "dudosa":
                dudosas += 1
            mensaje_id = f"{payload.device_serial}:{payload.seq}:{r.tipo}"
            try:
                res = lec_model.insertar_lectura(
                    float(r.valor_crudo), calidad, mensaje_id, id_sens, id_mag)
            except mysql.connector.Error as e:
                if e.errno == 1452:
                    errores.append(f"FK inexistente para tipo '{r.tipo}'")
                    continue
                raise
            if res["duplicada"]:
                duplicadas += 1
            else:
                insertadas += 1
        if insertadas:
            lec_model.touch_dispositivo(dev["id_dispositivo"])
    except mysql.connector.Error as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": f"DB: {e.msg}"})
    return {"ok": True, "insertadas": insertadas, "duplicadas": duplicadas,
            "dudosas": dudosas, "errores": errores}


@router.get("/api/ultimas")
def ultimas(limit: int = 50):
    return {"ok": True, "lecturas": lec_model.get_ultimas(limit)}


@router.get("/datos")
def datos(request: Request):
    # Vista de testeo: a proposito sin sesion ni diseno, solo tabla cruda.
    return templates.TemplateResponse(
        request, "datos/index.html",
        {"request": request, "lecturas": lec_model.get_ultimas(50)})
