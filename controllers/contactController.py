"""Pagina publica Contáctanos: formulario de asunto y contenido que llega
por correo al buzón del equipo (CONTACTO_EMAIL en .env)."""
from uuid import UUID

from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessionsConfig import SessionData, getOptionalSession
from models import usersModel as user_model
from utils import emailUtils as email_utils
from utils import authUtils as user_utils
from utils.commonUtils import userSessionContext
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")

MAX_ASUNTO = 200
MAX_CONTENIDO = 5000
DESTINO_DEFECTO = "luis.gamboa@puentemaipo.cl"


def _destinoContacto():
    import os
    return os.getenv("CONTACTO_EMAIL") or DESTINO_DEFECTO


def showContacto(request: Request,
                 sesion: SessionData | None = Depends(getOptionalSession)):
    usuario = user_model.getUserById(sesion.id_usuario) if sesion else None
    flash_msg, old, flash_ok = popFormFlash(request)
    if usuario is not None:
        old.setdefault("nombre", usuario["nombre"] or "")
        old.setdefault("correo", usuario["email"] or "")
    ctx = (userSessionContext(sesion) if sesion is not None
           else {"logged": None, "iniciales": None})
    return templates.TemplateResponse(
        request, "contacto/contacto.html",
        {"request": request, "old": old,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         "destino": _destinoContacto(),
         "sesion_activa": sesion is not None,
         "usuario_email": usuario["email"] if usuario else None,
         **ctx})


async def enviarContacto(request: Request,
                         asunto: str = Form(""),
                         contenido: str = Form(""),
                         nombre: str = Form(""),
                         correo: str = Form(""),
                         origen: str = Form(""),
                         sesion: SessionData | None = Depends(getOptionalSession)):
    # El formulario vive en la landing (/home#contacto) y en la pagina
    # directa (/contacto): se vuelve al punto de origen tras el envio.
    volver = "/home#contacto" if origen == "home" else "/contacto"
    usuario = user_model.getUserById(sesion.id_usuario) if sesion else None
    if usuario is not None:
        # Con sesion activa la identidad es la de la cuenta (no se edita).
        nombre = usuario["nombre"] or ""
        correo = usuario["email"] or ""
    asunto = (asunto or "").strip()
    contenido = (contenido or "").strip()
    nombre = (nombre or "").strip()
    correo = (correo or "").strip()
    viejo = {"asunto": asunto, "contenido": contenido,
             "nombre": nombre, "correo": correo}

    def volverConError(mensaje):
        flashForm(request, mensaje, viejo)
        return RedirectResponse(volver, status_code=303)

    if not asunto:
        return volverConError("El asunto es obligatorio.")
    if len(asunto) > MAX_ASUNTO:
        return volverConError(f"El asunto no puede superar {MAX_ASUNTO} caracteres.")
    if not contenido:
        return volverConError("El contenido del mensaje es obligatorio.")
    if len(contenido) > MAX_CONTENIDO:
        return volverConError(f"El contenido no puede superar {MAX_CONTENIDO} caracteres.")

    # Identidad del remitente: opcional para anonimos, fija para sesiones.
    remitente = {"texto": "Anónimo", "correo": None}
    if correo:
        correo_limpio, error_email = user_utils.validateEmail(correo)
        if error_email:
            return volverConError(error_email)
        remitente = {"texto": f"{nombre} <{correo_limpio}>" if nombre else correo_limpio,
                     "correo": correo_limpio}
    elif nombre:
        remitente = {"texto": nombre}

    try:
        email_utils.sendContactoEmail(asunto, contenido, remitente)
    except Exception as e:
        return volverConError(f"No se pudo enviar el mensaje: {e}. "
                              "Intenta nuevamente en unos minutos.")
    flashForm(request, "Mensaje enviado correctamente. Te responderemos al "
                       "correo indicado.", ok=True)
    return RedirectResponse(volver, status_code=303)
