"""
    Controlador de usuarios (MVC: Controller).
    Solo gestión de usuarios: listado, detalle y edición.
    Las consultas viven en models/usersModel.py. Las rutas viven en
    routers/usersRoutes.py.
"""

# controllers/usersController.py
from uuid import UUID

import mysql.connector
from fastapi import Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessionsConfig import (
    SessionData,
    cookie as session_cookie,
    verificador,
)

# El controlador usa el modelo y los mensajes flash.
from models import usersModel as user_model
from utils.flashUtils import flashForm, popFormFlash

# Lo que en js se hace con app.set('view engine', 'ejs'), en fastapi se hace con Jinja2Templates()
# la carpeta templates debe estar en la raiz del proyecto, al mismo nivel que main.py.
templates = Jinja2Templates(directory="templates")


# index — lista todos los usuarios (ruta protegida: exige sesión)
def listUsers(request: Request, id_sesion: UUID = Depends(session_cookie), sesion: SessionData = Depends(verificador)):
    users = user_model.getAllUsers()
    flash_msg, _, flash_ok = popFormFlash(request)
    # Retorna la plantilla index.html, y le pasa como contexto la variable users, que contiene los registros de la tabla usuarios.
    return templates.TemplateResponse(request, "users-login/index.html", {"request": request,
    "users": users, "flash_msg": flash_msg, "flash_ok": flash_ok})


# show muestra un usuario por id (SELECT ... WHERE id_usuario = %s)
def showUser(request: Request,
         id_usuario: int,
         id_sesion: UUID = Depends(session_cookie),
         sesion: SessionData = Depends(verificador)
         ):
    user = user_model.getUserById(id_usuario)
    if user is None:
        return templates.TemplateResponse(request, "users-login/index.html", {"request": request})

    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "users-login/show.html",
        {"request": request, "user": user, "flash_msg": flash_msg, "flash_ok": flash_ok})


def showEditUserForm(request: Request,
              id_usuario: int,
              id_sesion: UUID = Depends(session_cookie),
              sesion: SessionData = Depends(verificador)
              ):
    user = user_model.getUserById(id_usuario)
    if user is None:
        return templates.TemplateResponse(request, "users-login/index.html", {"request": request})

    return templates.TemplateResponse(request, "users-login/edit.html", {"request": request, "user": user})


def updateUser(
    request: Request,
    id_usuario: int,
    id_sesion: UUID = Depends(session_cookie),
    sesion: SessionData = Depends(verificador),
    nombre: str = Form(...),
    apellido: str = Form(""),
    email: str = Form(...),
    telefono: str = Form(""),
    id_organizacion: str = Form("")
    ):

    form_data = {"nombre": nombre,
                 "apellido": apellido,
                 "email": email,
                 "telefono": telefono,
                 "id_organizacion": id_organizacion
                 }

    try:
        user_model.updateUser(
            id_usuario,
            form_data["nombre"],
            form_data["apellido"],
            form_data["email"],
            form_data["telefono"],
            int(form_data["id_organizacion"]) if form_data["id_organizacion"] else None,
        )
        flashForm(request, "Usuario actualizado correctamente.", ok=True)
        return RedirectResponse(f"/users/{id_usuario}", status_code=303)
    except mysql.connector.Error as e:
        return templates.TemplateResponse(request, "users-login/show.html", {"request": request, "user": form_data, "error": "Error al actualizar el usuario"})
