"""Gestión de reglas de alerta del panel admin desde la ficha del dispositivo (HU-013).
Guardar una regla dispara el recálculo del estado de alertas de la zona. Las reglas
no se borran: solo se activan o desactivan para conservar su historial."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse

from config.sessionsConfig import SessionData, cookie as session_cookie, requireAdminUser
from models import rulesModel as rule_model
from models import alertsModel as alert_model
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
    # La vigencia solo puede empezar hoy o en el futuro, y terminar hoy o después.
    hoy = date.today()
    if desde is not None and desde.date() < hoy:
        return None, "la vigencia desde no puede ser anterior a hoy"
    if hasta is not None and hasta.date() < hoy:
        return None, "la vigencia hasta no puede ser anterior a hoy"
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
               vigencia_hasta: str = Form("")):
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
    # El estado activo/inactivo se cambia solo con el boton Activar/Desactivar:
    # editar la regla conserva el estado actual.
    rule_model.updateRule(id_regla, regla["operador"], regla["valor_umbral"],
                          regla["severidad"], regla["duracion_minima_seg"],
                          regla["vigencia_desde"], regla["vigencia_hasta"],
                          bool(regla_actual["activa"]), regla["id_magnitud"])
    if _recalc(request, dev):
        flashForm(request, "Regla actualizada. Estado de los dispositivos de la zona recalculado.",
                  ok=True)
    return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)


def toggleRule(request: Request,
               id_device: int,
               id_regla: int,
               id_sesion: UUID = Depends(session_cookie),
               sesion: SessionData = Depends(requireAdminUser)):
    """Activa o desactiva una regla. Al desactivarla se resuelven sus alertas
    abiertas, porque el motor deja de evaluarla y quedarian colgadas."""
    dev = _deviceGuard(request, id_device, sesion)
    if dev is None:
        return RedirectResponse("/dashboard", status_code=303)
    regla_actual = rule_model.getRuleById(id_regla)
    if regla_actual is None or regla_actual["id_zona"] != dev["id_zona"]:
        flashForm(request, "La regla no pertenece a la zona de este dispositivo.")
        return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)
    activar = not bool(regla_actual["activa"])
    if not activar:
        alert_model.resolveAlertasDeRegla(
            id_regla, "Regla desactivada por el administrador")
    rule_model.setRuleActive(id_regla, activar)
    if _recalc(request, dev):
        if activar:
            flashForm(request, "Regla activada. Estado de la zona recalculado.", ok=True)
        else:
            flashForm(request, "Regla desactivada. Sus alertas abiertas se resolvieron.",
                      ok=True)
    return RedirectResponse(f"/dashboard/devices/{id_device}", status_code=303)
