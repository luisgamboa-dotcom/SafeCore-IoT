"""Admin users management."""
from uuid import UUID

import mysql.connector
from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from config.sessionsConfig import SessionData, cookie as session_cookie, requireAdminUser
from models import usersModel as user_model
from models import organizationsModel as org_model
from utils.commonUtils import adminContext
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")


def editFormData(id_user):
    user = user_model.getUserById(id_user)
    if user is None:
        return None
    roles = user_model.getUserRoles(id_user)
    return {"user": user, "rol_actual": roles[0] if roles else None,
            "organizaciones": org_model.getAllOrganizations(solo_activas=True),
            "roles": user_model.getAllRoles(),
            "estados": user_model.getAllUserStates()}


def showUsersPage(request: Request,
                  id_sesion: UUID = Depends(session_cookie),
                  sesion: SessionData = Depends(requireAdminUser),
                  q: str = ""):
    q = (q or "").strip() or None
    usuarios = user_model.getAllUsersWithDetails(q)
    total = len(user_model.getAllUsersWithDetails())
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/users.html",
        {"request": request, "usuarios": usuarios, "q": q or "",
         "total": total, "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def showEditUserForm(request: Request,
                     id_user: int,
                     id_sesion: UUID = Depends(session_cookie),
                     sesion: SessionData = Depends(requireAdminUser)):
    ctx = editFormData(id_user)
    if ctx is None:
        return RedirectResponse("/admin/users", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/edit.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok, **ctx,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def updateUserFromAdmin(request: Request,
                        id_user: int,
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
            id_user, nombre.strip(), apellido.strip(), email.strip(),
            int(id_organizacion) if id_organizacion else None, int(id_estado))
        user_model.replaceUserRole(id_user, int(id_rol))
    except mysql.connector.Error as e:
        if e.errno == 1062:
            flashForm(request, "Ese correo ya está registrado por otro usuario.")
        elif e.errno == 1452:
            flashForm(request, "Organización, rol o estado inválido.")
        else:
            flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse(f"/admin/users/{id_user}/edit", status_code=303)
    flashForm(request, "Usuario actualizado correctamente.", ok=True)
    return RedirectResponse("/admin/users", status_code=303)
