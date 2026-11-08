from uuid import UUID

from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessionsConfig import SessionData, cookie as session_cookie, verificador
from models import usersModel as user_model
from utils import authUtils as user_utils
from utils.commonUtils import userSessionContext
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")


def showMyProfile(request: Request,
                  id_sesion: UUID = Depends(session_cookie),
                  sesion: SessionData = Depends(verificador)):
    usuario = user_model.getUserById(sesion.id_usuario)
    if usuario is None:
        return RedirectResponse("/users/logout", status_code=303)
    flash_msg, old, flash_ok = popFormFlash(request)

    viejo = old or {"nombre": usuario["nombre"], "apellido": usuario["apellido"],
                    "telefono": usuario["telefono"] or ""}
    return templates.TemplateResponse(
        request, "users-perfil/perfil.html",
        {"request": request, "usuario": usuario, "old": viejo,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **userSessionContext(sesion)})


async def updateMyProfile(request: Request,
                          id_sesion: UUID = Depends(session_cookie),
                          sesion: SessionData = Depends(verificador),
                          nombre: str = Form(...),
                          apellido: str = Form(...),
                          telefono: str = Form("")):
    viejo = {"nombre": nombre, "apellido": apellido, "telefono": telefono}

    def volverConError(mensaje):
        flashForm(request, mensaje, viejo)
        return RedirectResponse("/users/perfil", status_code=303)


    datos = user_utils.normalizeForm({"nombre": nombre, "apellido": apellido,
                                      "telefono": telefono})
    if not datos["nombre"] or not datos["apellido"]:
        return volverConError("Nombre y apellido son obligatorios.")
    telefono_normalizado, error_telefono = user_utils.validateChileanPhone(datos["telefono"])
    if error_telefono:
        return volverConError(error_telefono)
    try:
        user_model.updatePerfil(sesion.id_usuario, datos["nombre"],
                               datos["apellido"], telefono_normalizado)
    except Exception as e:
        return volverConError(f"Error al guardar: {e}")
    flashForm(request, "Datos actualizados correctamente.", ok=True)
    return RedirectResponse("/users/perfil", status_code=303)
