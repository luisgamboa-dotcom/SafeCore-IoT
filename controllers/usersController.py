"""Admin users management."""
from typing import List
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
from models import organizationsModel as org_model
from utils.commonUtils import adminContext
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")


ROL_PROTEGIDO = "Superadmin"


def _nivelPoder(nombres_roles):
    if ROL_PROTEGIDO in nombres_roles:
        return 3
    if "Administrador" in nombres_roles:
        return 2
    return 1


def _checkEditAccess(sesion, id_user):
    """(permitido, auto_edicion) según jerarquía: solo el Superadmin
    administra cuentas de Administrador/Superadmin; un Administrador
    puedo editar sus propios datos pero sin cambiar roles ni estado."""
    roles_actor = user_model.getUserRoles(sesion.id_usuario)
    if _nivelPoder(roles_actor) >= 3:
        return True, id_user == sesion.id_usuario
    if id_user == sesion.id_usuario:
        return True, True
    return _nivelPoder(user_model.getUserRoles(id_user)) < 2, False


def editFormData(id_user):
    user = user_model.getUserById(id_user)
    if user is None:
        return None
    roles_usuario = user_model.getUserRoles(id_user)
    return {"user": user, "roles_usuario": roles_usuario,
            "organizaciones": org_model.getAllOrganizations(solo_activas=True),
            "roles": user_model.getAllRoles(),
            "estados": user_model.getAllUserStates()}


def showUsersPage(request: Request,
                  id_sesion: UUID = Depends(session_cookie),
                  sesion: SessionData = Depends(requireAdminUser),
                  q: str = "",
                  sort: str = "id",
                  dir: str = "asc",
                  estado: str = "",
                  rol: str = "",
                  org: str = ""):
    q = (q or "").strip() or None
    usuarios = user_model.getAllUsersWithDetails(
        q, sort_by=sort, sort_dir=dir, estado=estado or None,
        rol=rol or None, id_organizacion=org or None)
    total = len(user_model.getAllUsersWithDetails())
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/users.html",
        {"request": request, "usuarios": usuarios, "q": q or "",
         "total": total,
         "f_sort": sort, "f_dir": dir, "f_estado": estado or "",
         "f_rol": rol or "", "f_org": org or "",
         "organizaciones": org_model.getAllOrganizations(),
         "roles": user_model.getAllRoles(),
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def showEditUserForm(request: Request,
                     id_user: int,
                     id_sesion: UUID = Depends(session_cookie),
                     sesion: SessionData = Depends(requireAdminUser)):
    permitido, auto_edicion = _checkEditAccess(sesion, id_user)
    if not permitido:
        flashForm(request, "Solo el Superadmin puede administrar cuentas de Administrador.")
        return RedirectResponse("/admin/users", status_code=303)
    ctx = editFormData(id_user)
    if ctx is None:
        return RedirectResponse("/admin/users", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/edit.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok, **ctx,
         "auto_edicion_limitada": auto_edicion,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def updateUserFromAdmin(request: Request,
                        id_user: int,
                        id_sesion: UUID = Depends(session_cookie),
                        sesion: SessionData = Depends(requireAdminUser),
                        nombre: str = Form(...),
                        apellido: str = Form(...),
                        email: str = Form(...),
                        id_organizacion: str = Form(""),
                        id_roles: List[str] = Form(default=[]),
                        id_estado: str = Form("")):
    permitido, auto_edicion = _checkEditAccess(sesion, id_user)
    if not permitido:
        flashForm(request, "Solo el Superadmin puede administrar cuentas de Administrador.")
        return RedirectResponse("/admin/users", status_code=303)
    roles_actor = user_model.getUserRoles(sesion.id_usuario)
    es_super = ROL_PROTEGIDO in roles_actor
    user_actual = user_model.getUserById(id_user)
    # Autoedición limitada (admin editándose a sí mismo): roles y estado quedan como están.
    estado_elegido = int(id_estado) if str(id_estado).strip().isdigit() else None
    estado_final = None
    if auto_edicion and not es_super:
        estado_final = user_actual["id_usuario_estado"]
    elif estado_elegido is not None:
        estado_final = estado_elegido
    else:
        estado_final = user_actual["id_usuario_estado"]
    ids_elegidos = {int(r) for r in id_roles if str(r).strip().isdigit()}
    if auto_edicion and not es_super:
        ids_elegidos = {row["id_rol"] for row in user_model.getUserRoleIds(id_user)}
    elif not es_super:
        # Un Administrador solo puede asignar roles por debajo de su nivel.
        ids_bajos = {r["id_catalogo_rol"] for r in user_model.getAllRoles()
                     if _nivelPoder([r["nombre_rol"]]) < 2}
        ids_elegidos &= ids_bajos
    ids_retenidos = {row["id_rol"] for row in user_model.getUserRoleIds(id_user)
                     if row["nombre_rol"] == ROL_PROTEGIDO}
    ids_finales = ids_elegidos | ids_retenidos
    nombres_finales = {r["nombre_rol"] for r in user_model.getAllRoles()
                       if r["id_catalogo_rol"] in ids_finales}
    # Un Supervisor siempre supervisa una organizacion concreta.
    if "Supervisor" in nombres_finales and not id_organizacion.strip():
        flashForm(request, "El rol Supervisor requiere una organización asignada.")
        return RedirectResponse(f"/admin/users/{id_user}/edit", status_code=303)
    try:
        user_model.updateUser(
            id_user, nombre.strip(), apellido.strip(), email.strip(),
            int(id_organizacion) if id_organizacion else None, estado_final)
        user_model.replaceUserRoles(id_user, list(ids_finales))
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
