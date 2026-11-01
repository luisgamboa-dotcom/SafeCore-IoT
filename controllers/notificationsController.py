"""Centro de notificaciones: listado de los avisos del usuario y lectura."""
from uuid import UUID

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessionsConfig import SessionData, cookie as session_cookie, verificador
from models import notificationsModel as notif_model
from utils.commonUtils import userSessionContext
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")


def showNotificacionesPage(request: Request,
                           id_sesion: UUID = Depends(session_cookie),
                           sesion: SessionData = Depends(verificador)):
    """HU-021: centro de notificaciones del usuario con asunto, contenido,
    canal, estado de envío, fechas y enlace a la alerta de origen.
    ?estado=sin_leer filtra las aún sin leer; sin filtro, todas."""
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
    """HU-021: botón 'Marcar leída' de una notificación del propio usuario.
    El guard de dueño vive en el modelo (0 filas = no existe, ya leída o ajena)."""
    ok = notif_model.marcarLeida(id_notificacion, sesion.id_usuario)
    if ok:
        flashForm(request, "Notificación marcada como leída.", ok=True)
    else:
        flashForm(request, "La notificación no existe, no es tuya o ya está leída.")
    return RedirectResponse("/dashboard/notificaciones", status_code=303)
