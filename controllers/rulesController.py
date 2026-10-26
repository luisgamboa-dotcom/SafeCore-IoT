"""Gestión de reglas de alerta del panel admin desde la ficha del dispositivo (HU-013).
Guardar una regla dispara el recálculo del estado de alertas de la zona."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

import mysql.connector
from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse

from config.sessionsConfig import SessionData, cookie as session_cookie, requireAdminUser
from models import rulesModel as rule_model
from models import devicesModel as dev_model
from utils.flashUtils import flashForm


# Frase base "Valores invalidos" exigida por la checklist de aceptación.
_INVALID_MSG = "Valores inválidos"


def _parseRuleForm(id_magnitud, operador, valor_umbral, severidad,
                   duracion_minima_seg, vigencia_desde, vigencia_hasta):
    """Devuelve (regla, error). regla es None siempre que error no sea None."""
    try:
        id_magnitud = int(str(id_magnitud).strip())
    except (TypeError, ValueError):
        return None, "magnitud no válida"
    if id_magnitud not in {m["id_magnitud"] for m in rule_model.getMagnitudes()}:
        return None, "magnitud no existente"
    if operador not in rule_model.OPERADORES:
        return None, "operador no permitido"
    try:
        umbral = Decimal(str(valor_umbral).strip().replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return None, "valor umbral no numérico"
    if umbral < 0:
        # Umbral negativo incoherente con las magnitudes del sistema.
        return None, "umbral negativo"
    if severidad not in rule_model.SEVERIDADES:
        return None, "severidad no permitida"
    try:
        duracion = int(str(duracion_minima_seg).strip())
    except (TypeError, ValueError):
        return None, "duración no numérica"
    if duracion < 0 or duracion > rule_model.MAX_DURACION_S:
        return None, "duración fuera de rango"
    desde = _parseVigencia(vigencia_desde)
    hasta = _parseVigencia(vigencia_hasta)
    if desde == "x" or hasta == "x":
        return None, "fecha de vigencia inválida"
    if desde is not None and hasta is not None and hasta <= desde:
        return None, "vigencia incoherente (fin anterior al inicio)"
    regla = {"id_magnitud": id_magnitud, "operador": operador, "valor_umbral": umbral,
             "severidad": severidad, "duracion_minima_seg": duracion,
             "vigencia_desde": desde, "vigencia_hasta": hasta}
    return regla, None


def _parseVigencia(valor):
    valor = (str(valor or "").strip() or None)
    if valor is None:
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return "x"


def _deviceGuard(request, id_device, sesion):
    """El dispositivo debe existir (el alcance por organización se hereda del chequeo de la ruta de detalle)."""
    dev = dev_model.getDeviceDetail(id_device)
    if dev is None:
        flashForm(request, "El dispositivo no existe.")
        return None
    return dev


def _recalc(request, dev):
    """Recalcula la zona; si falla, avisa por flash pero conserva el cambio."""
    try:
        rule_model.evaluateZone(dev["id_zona"])
        return True
    except Exception:
        flashForm(request, "La regla se guardó, pero no se pudo recalcular el estado de la zona.")
        return False


def storeRule(request: Request,
              id_device: int,
              id_sesion: UUID = Depends(session_cookie),
              sesion: SessionData = Depends(requireAdminUser),
              id_magnitud: str = Form(...),
              operador: str = Form(...),
              valor_umbral: str = Form(...),
              severidad: str = Form(...),
              duracion_minima_seg: str = Form(...),
              vigencia_desde: str = Form(""),
              vigencia_hasta: str = Form(""),
              activa: str = Form("")):
    dev = _deviceGuard(request, id_device, sesion)
    if dev is None:
        return RedirectResponse("/dashboard", status_code=303)
    regla, error = _parseRuleForm(id_magnitud, operador, valor_umbral, severidad,
                                  duracion_minima_seg, vigencia_desde,
                                  vigencia_hasta)
    if error is not None:
        flashForm(request, f"{_INVALID_MSG}: {error}")
        return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)
    rule_model.createRule(regla["operador"], regla["valor_umbral"], regla["severidad"],
                          regla["duracion_minima_seg"], regla["vigencia_desde"],
                          regla["vigencia_hasta"], activa == "1",
                          regla["id_magnitud"], dev["id_zona"])
    if _recalc(request, dev):
        flashForm(request, "Regla guardada. Estado de los dispositivos de la zona recalculado.",
                  ok=True)
    return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)


def updateRule(request: Request,
               id_device: int,
               id_regla: int,
               id_sesion: UUID = Depends(session_cookie),
               sesion: SessionData = Depends(requireAdminUser),
               id_magnitud: str = Form(...),
               operador: str = Form(...),
               valor_umbral: str = Form(...),
               severidad: str = Form(...),
               duracion_minima_seg: str = Form(...),
               vigencia_desde: str = Form(""),
               vigencia_hasta: str = Form(""),
               activa: str = Form("")):
    dev = _deviceGuard(request, id_device, sesion)
    if dev is None:
        return RedirectResponse("/dashboard", status_code=303)
    regla_actual = rule_model.getRuleById(id_regla)
    if regla_actual is None or regla_actual["id_zona"] != dev["id_zona"]:
        flashForm(request, "La regla no pertenece a la zona de este dispositivo.")
        return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)
    regla, error = _parseRuleForm(id_magnitud, operador, valor_umbral, severidad,
                                  duracion_minima_seg, vigencia_desde,
                                  vigencia_hasta)
    if error is not None:
        flashForm(request, f"{_INVALID_MSG}: {error}")
        return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)
    rule_model.updateRule(id_regla, regla["operador"], regla["valor_umbral"],
                          regla["severidad"], regla["duracion_minima_seg"],
                          regla["vigencia_desde"], regla["vigencia_hasta"],
                          activa == "1", regla["id_magnitud"])
    if _recalc(request, dev):
        flashForm(request, "Regla actualizada. Estado de los dispositivos de la zona recalculado.",
                  ok=True)
    return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)


def deleteRule(request: Request,
               id_device: int,
               id_regla: int,
               id_sesion: UUID = Depends(session_cookie),
               sesion: SessionData = Depends(requireAdminUser)):
    dev = _deviceGuard(request, id_device, sesion)
    if dev is None:
        return RedirectResponse("/dashboard", status_code=303)
    regla_actual = rule_model.getRuleById(id_regla)
    if regla_actual is None or regla_actual["id_zona"] != dev["id_zona"]:
        flashForm(request, "La regla no pertenece a la zona de este dispositivo.")
        return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)
    try:
        rule_model.deleteRule(id_regla)
    except mysql.connector.Error as e:
        if e.errno == 1451:
            # Las alertas históricas referencian la regla (RESTRICT): desactivar en su lugar.
            rule_model.updateRule(id_regla, regla_actual["operador"],
                                  regla_actual["valor_umbral"], regla_actual["severidad"],
                                  regla_actual["duracion_minima_seg"],
                                  regla_actual["vigencia_desde"],
                                  regla_actual["vigencia_hasta"], False,
                                  regla_actual["id_magnitud"])
            _recalc(request, dev)
            flashForm(request, "La regla tiene alertas registradas: se desactivó en lugar de borrarse.",
                      ok=True)
            return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)
        flashForm(request, f"No se pudo borrar la regla: {e.msg}")
        return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)
    except Exception as e:
        flashForm(request, f"No se pudo borrar la regla: {e}")
        return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)
    if _recalc(request, dev):
        flashForm(request, "Regla eliminada. Estado de los dispositivos de la zona recalculado.",
                  ok=True)
    return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)
