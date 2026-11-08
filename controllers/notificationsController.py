from uuid import UUID

from fastapi import Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessionsConfig import SessionData, cookie as session_cookie, verificador
from models import notificationsModel as notif_model
from models import usersModel as user_model
from utils import authUtils as user_utils
from utils.commonUtils import userSessionContext
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")

PRIORIDADES = (1, 2, 3)


def showNotificacionesPage(request: Request,
                           id_sesion: UUID = Depends(session_cookie),
                           sesion: SessionData = Depends(verificador)):
    estado = request.query_params.get("estado", "")
    solo_no_leidas = (estado == "sin_leer")
    if not solo_no_leidas:
        estado = None
    try:
        notificaciones = notif_model.getNotificacionesUsuario(
            sesion.id_usuario, limite=100, solo_no_leidas=solo_no_leidas)
        total_todas = notif_model.countUsuario(sesion.id_usuario)
        total_sin_leer = notif_model.countNoLeidas(sesion.id_usuario)
    except Exception:
        notificaciones = []
        total_todas = 0
        total_sin_leer = 0
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(
        request, "datos/notificaciones.html",
        {"request": request, "notificaciones": notificaciones,
         "estado_actual": estado,
         "total_todas": total_todas, "total_sin_leer": total_sin_leer,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **userSessionContext(sesion)})


def marcarLeidaNotificacion(request: Request,
                            id_notificacion: int,
                            id_sesion: UUID = Depends(session_cookie),
                            sesion: SessionData = Depends(verificador)):
    ok = notif_model.marcarLeida(id_notificacion, sesion.id_usuario)
    if ok:
        flashForm(request, "Notificación marcada como leída.", ok=True)
    else:
        flashForm(request, "La notificación no existe, no es tuya o ya está leída.")
    return RedirectResponse("/dashboard/notificaciones", status_code=303)




def showConfigCanales(request: Request,
                      id_sesion: UUID = Depends(session_cookie),
                      sesion: SessionData = Depends(verificador)):
    perfil = notif_model.getPerfilCanales(sesion.id_usuario)
    usuario = user_model.getUserById(sesion.id_usuario)
    flash_msg, old, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(
        request, "datos/notificaciones-config.html",
        {"request": request, "perfil": perfil,
         "email_cuenta": usuario["email"] if usuario else "",
         "flash_msg": flash_msg, "flash_ok": flash_ok, "old": old,
         **userSessionContext(sesion)})


def saveConfigCanales(
    request: Request,
    id_sesion: UUID = Depends(session_cookie),
    sesion: SessionData = Depends(verificador),
    web_habilitado: str = Form(""),
    web_prioridad: str = Form(""),
    email_habilitado: str = Form(""),
    email_prioridad: str = Form(""),
    email_destino: str = Form(""),
    ):
    filas = []
    if web_habilitado:
        prioridad_web = _prioridadValida(web_prioridad)
        if prioridad_web is None:
            return redirConfigConError(request, "La prioridad del canal web debe ser 1, 2 o 3.")
        filas.append({"id_canal": notif_model.CANAL_WEB, "habilitado": True,
                      "destino": None, "prioridad": prioridad_web})

    destino_email = user_model.getUserById(sesion.id_usuario)["email"] \
        if email_habilitado and not email_destino.strip() else email_destino
    if email_habilitado:
        prioridad_email = _prioridadValida(email_prioridad)
        if prioridad_email is None:
            return redirConfigConError(request, "La prioridad del canal correo debe ser 1, 2 o 3.")
        correo_limpio, error_email = user_utils.validateEmail(destino_email.strip())
        if error_email:
            return redirConfigConError(request, error_email,
                                       {"email_destino": email_destino})
        filas.append({"id_canal": notif_model.CANAL_EMAIL, "habilitado": True,
                      "destino": correo_limpio, "prioridad": prioridad_email})

    notif_model.savePerfilCanales(sesion.id_usuario, filas)
    if filas:
        flashForm(request, "Canales de notificación guardados correctamente.", ok=True)
    else:
        flashForm(request, "No recibirás ninguna notificación.")
    return RedirectResponse("/dashboard/notificaciones/configurar", status_code=303)


def _prioridadValida(valor):
    try:
        prioridad = int(valor)
    except (TypeError, ValueError):
        return None
    return prioridad if prioridad in PRIORIDADES else None


def redirConfigConError(request, mensaje, old=None):
    flashForm(request, mensaje, old)
    return RedirectResponse("/dashboard/notificaciones/configurar", status_code=303)
