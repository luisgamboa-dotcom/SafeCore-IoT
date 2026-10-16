"""Controlador de administración: gestión con rol Administrador."""
from uuid import UUID

import mysql.connector
from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from utils.flashUtils import flashForm, popFormFlash

from config.sessionsConfig import (
    SessionData,
    cookie as session_cookie,
    requireAdminUser,
)

from models import usersModel as user_model

templates = Jinja2Templates(directory="templates")


# users — gestión de usuarios con rol y estado (solo Administrador)
def showUsersPage(request: Request,
                  id_sesion: UUID = Depends(session_cookie),
                  sesion: SessionData = Depends(requireAdminUser),
                  q: str = ""):
    q = (q or "").strip() or None
    usuarios = user_model.getAllUsersWithDetails(q)
    total = len(user_model.getAllUsersWithDetails())
    flash_msg, _, flash_ok = popFormFlash(request)
    admin = user_model.getUserById(sesion.id_usuario)
    iniciales = admin["nombre"][0] + (admin["apellido"][0] if admin and admin["apellido"] else "") if admin else ""
    return templates.TemplateResponse(request, "admin/users.html",
        {"request": request, "usuarios": usuarios, "is_admin": True, "q": q or "",
         "total": total, "flash_msg": flash_msg, "flash_ok": flash_ok,
         "admin_nombre": admin["nombre"] if admin else "Admin",
         "iniciales": iniciales, "id_usuario": sesion.id_usuario})


def _formularios_edicion(id_usuario):
    user = user_model.getUserById(id_usuario)
    if user is None:
        return None
    roles = user_model.getUserRoles(id_usuario)
    return {"user": user, "rol_actual": roles[0] if roles else None,
            "organizaciones": user_model.getAllOrganizations(),
            "roles": user_model.getAllRoles(),
            "estados": user_model.getAllUserStates()}


# edit — muestra el panel de edición de un usuario (solo Administrador)
def showEditUserForm(request: Request,
                     id_usuario: int,
                     id_sesion: UUID = Depends(session_cookie),
                     sesion: SessionData = Depends(requireAdminUser)):
    ctx = _formularios_edicion(id_usuario)
    if ctx is None:
        return RedirectResponse("/admin/users", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    admin = user_model.getUserById(sesion.id_usuario)
    iniciales = admin["nombre"][0] + (admin["apellido"][0] if admin and admin["apellido"] else "") if admin else ""
    return templates.TemplateResponse(request, "admin/edit.html",
        {"request": request, "is_admin": True, "flash_msg": flash_msg, "flash_ok": flash_ok,
         "admin_nombre": admin["nombre"] if admin else "Admin",
         "iniciales": iniciales, "id_usuario": sesion.id_usuario, **ctx})


# update — guarda los datos editados de un usuario (solo Administrador)
def updateUserFromAdmin(request: Request,
                        id_usuario: int,
                        id_sesion: UUID = Depends(session_cookie),
                        sesion: SessionData = Depends(requireAdminUser),
                        nombre: str = Form(...),
                        apellido: str = Form(...),
                        email: str = Form(...),
                        id_organizacion: str = Form(""),
                        id_rol: str = Form(...),
                        id_estado: str = Form(...)):
    try:
        user_model.updateUser(
            id_usuario, nombre.strip(), apellido.strip(), email.strip(),
            int(id_organizacion) if id_organizacion else None, int(id_estado))
        user_model.replaceUserRole(id_usuario, int(id_rol))
    except mysql.connector.Error as e:
        if e.errno == 1062:
            flashForm(request, "Ese correo ya está registrado por otro usuario.")
        elif e.errno == 1452:
            flashForm(request, "Organización, rol o estado inválido.")
        else:
            flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse(f"/admin/users/{id_usuario}/edit", status_code=303)
    flashForm(request, "Usuario actualizado correctamente.", ok=True)
    return RedirectResponse("/admin/users", status_code=303)
