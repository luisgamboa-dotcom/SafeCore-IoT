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
from models import organizationsModel as org_model
from models import instalacionesModel as inst_model
from models import zonasModel as zona_model

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
            "organizaciones": org_model.getAllOrganizations(solo_activas=True),
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


# panel — portada del panel de administración (solo Administrador)
def showAdminPanel(request: Request,
                   id_sesion: UUID = Depends(session_cookie),
                   sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/index.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok,
         **_contexto_admin(sesion)})


def _contexto_admin(sesion):
    admin = user_model.getUserById(sesion.id_usuario)
    iniciales = admin["nombre"][0] + (admin["apellido"][0] if admin and admin["apellido"] else "") if admin else ""
    return {"is_admin": True,
            "admin_nombre": admin["nombre"] if admin else "Admin",
            "iniciales": iniciales, "id_usuario": sesion.id_usuario}


# organizations — listado + formulario de creación (solo Administrador)
def showOrganizationsPage(request: Request,
                          id_sesion: UUID = Depends(session_cookie),
                          sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    organizaciones = org_model.getAllOrganizations()
    return templates.TemplateResponse(request, "admin/organizations.html",
        {"request": request, "organizaciones": organizaciones,
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_contexto_admin(sesion)})


# organizations — guarda una organización nueva (solo Administrador)
def storeOrganization(request: Request,
                      id_sesion: UUID = Depends(session_cookie),
                      sesion: SessionData = Depends(requireAdminUser),
                      nombre: str = Form(...),
                      descripcion: str = Form("")):
    nombre = (nombre or "").strip()
    if not nombre:
        flashForm(request, "El nombre de la organización es obligatorio.")
        return RedirectResponse("/admin/organizations", status_code=303)
    try:
        org_model.createOrganization(nombre, (descripcion or "").strip() or None)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse("/admin/organizations", status_code=303)
    flashForm(request, "Organización creada correctamente.", ok=True)
    return RedirectResponse("/admin/organizations", status_code=303)


# organizations — formulario de creación en página aparte (solo Administrador)
def showCreateOrganizationForm(request: Request,
                               id_sesion: UUID = Depends(session_cookie),
                               sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/organizations-create.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok,
         **_contexto_admin(sesion)})


# organizations — detalle con miembros (solo Administrador)
def showOrganizationDetail(request: Request,
                           id_organizacion: int,
                           id_sesion: UUID = Depends(session_cookie),
                           sesion: SessionData = Depends(requireAdminUser)):
    org = org_model.getOrganizationById(id_organizacion)
    if org is None:
        flashForm(request, "La organización no existe.")
        return RedirectResponse("/admin/organizations", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/organizations-detail.html",
        {"request": request, "org": org,
         "tiene_relaciones": org_model.countOrganizationRelations(id_organizacion) > 0,
         "miembros": user_model.getUsersByOrganization(id_organizacion),
         "candidatos": user_model.getUsersOutsideOrganization(id_organizacion),
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_contexto_admin(sesion)})


# organizations — formulario de edición (solo Administrador)
def showEditOrganizationForm(request: Request,
                             id_organizacion: int,
                             id_sesion: UUID = Depends(session_cookie),
                             sesion: SessionData = Depends(requireAdminUser)):
    org = org_model.getOrganizationById(id_organizacion)
    if org is None:
        flashForm(request, "La organización no existe.")
        return RedirectResponse("/admin/organizations", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/organizations-edit.html",
        {"request": request, "org": org,
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_contexto_admin(sesion)})


# organizations — guarda los datos editados (solo Administrador)
def updateOrganization(request: Request,
                       id_organizacion: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(requireAdminUser),
                       nombre: str = Form(...),
                       descripcion: str = Form("")):
    nombre = (nombre or "").strip()
    if not nombre:
        flashForm(request, "El nombre de la organización es obligatorio.")
        return RedirectResponse(f"/admin/organizations/{id_organizacion}/edit", status_code=303)
    try:
        org_model.updateOrganization(id_organizacion, nombre, (descripcion or "").strip() or None)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse(f"/admin/organizations/{id_organizacion}/edit", status_code=303)
    flashForm(request, "Organización actualizada correctamente.", ok=True)
    return RedirectResponse(f"/admin/organizations/{id_organizacion}", status_code=303)


# organizations — elimina una org vacía o desactiva si tiene relaciones
def deleteOrganization(request: Request,
                       id_organizacion: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(requireAdminUser)):
    try:
        org_model.deleteOrganization(id_organizacion)
    except mysql.connector.Error as e:
        if e.errno in (1451, 1452):
            org_model.deactivateOrganization(id_organizacion)
            flashForm(request, "No se puede eliminar porque tiene usuarios o instalaciones: quedó desactivada.", ok=False)
        else:
            flashForm(request, f"Error al eliminar: {e.msg}")
        return RedirectResponse(f"/admin/organizations/{id_organizacion}", status_code=303)
    flashForm(request, "Organización eliminada correctamente.", ok=True)
    return RedirectResponse("/admin/organizations", status_code=303)


# organizations — quita un usuario de la org (queda "Sin organización")
def removeUserFromOrganization(request: Request,
                               id_organizacion: int,
                               id_sesion: UUID = Depends(session_cookie),
                               sesion: SessionData = Depends(requireAdminUser),
                               id_usuario: int = Form(...)):
    user_model.setUserOrganization(id_usuario, None)
    flashForm(request, "Usuario quitado de la organización.", ok=True)
    return RedirectResponse(f"/admin/organizations/{id_organizacion}", status_code=303)


# organizations — agrega un usuario a la org
def addUserToOrganization(request: Request,
                          id_organizacion: int,
                          id_sesion: UUID = Depends(session_cookie),
                          sesion: SessionData = Depends(requireAdminUser),
                          id_usuario: int = Form(...)):
    if org_model.getOrganizationById(id_organizacion) is None:
        flashForm(request, "La organización no existe.")
        return RedirectResponse("/admin/organizations", status_code=303)
    user_model.setUserOrganization(id_usuario, id_organizacion)
    flashForm(request, "Usuario agregado a la organización.", ok=True)
    return RedirectResponse(f"/admin/organizations/{id_organizacion}", status_code=303)


def _datos_direccion(form):
    return {"calle": (form.get("calle") or "").strip(),
            "numero": (form.get("numero") or "").strip(),
            "ciudad": (form.get("ciudad") or "").strip(),
            "region": (form.get("region") or "").strip(),
            "codigo_postal": (form.get("codigo_postal") or "").strip() or None}


# instalaciones — listado (solo Administrador)
def showInstalacionesPage(request: Request,
                          id_sesion: UUID = Depends(session_cookie),
                          sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/instalaciones.html",
        {"request": request, "instalaciones": inst_model.getAllInstalaciones(),
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_contexto_admin(sesion)})


# instalaciones — formulario de creación en página aparte (solo Administrador)
def showCreateInstalacionForm(request: Request,
                              id_sesion: UUID = Depends(session_cookie),
                              sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/instalaciones-create.html",
        {"request": request, "organizaciones": org_model.getAllOrganizations(solo_activas=True),
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_contexto_admin(sesion)})


# instalaciones — guarda una instalación nueva con su dirección (solo Administrador)
def storeInstalacion(request: Request,
                     id_sesion: UUID = Depends(session_cookie),
                     sesion: SessionData = Depends(requireAdminUser),
                     nombre: str = Form(...),
                     descripcion: str = Form(""),
                     id_organizacion: str = Form(...),
                     calle: str = Form(...),
                     numero: str = Form(...),
                     ciudad: str = Form(...),
                     region: str = Form(...),
                     codigo_postal: str = Form("")):
    nombre = (nombre or "").strip()
    if not nombre:
        flashForm(request, "El nombre de la instalación es obligatorio.")
        return RedirectResponse("/admin/instalaciones/create", status_code=303)
    for campo in (calle, numero, ciudad, region):
        if not (campo or "").strip():
            flashForm(request, "La dirección completa es obligatoria (calle, número, ciudad y región).")
            return RedirectResponse("/admin/instalaciones/create", status_code=303)
    try:
        inst_model.createInstalacion(
            nombre, (descripcion or "").strip() or None, int(id_organizacion),
            calle.strip(), numero.strip(), ciudad.strip(), region.strip(),
            (codigo_postal or "").strip() or None)
    except mysql.connector.Error as e:
        if e.errno in (1451, 1452):
            flashForm(request, "Organización inválida.")
        else:
            flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse("/admin/instalaciones/create", status_code=303)
    flashForm(request, "Instalación creada correctamente.", ok=True)
    return RedirectResponse("/admin/instalaciones", status_code=303)


# instalaciones — detalle con sus zonas (solo Administrador)
def showInstalacionDetail(request: Request,
                          id_instalacion: int,
                          id_sesion: UUID = Depends(session_cookie),
                          sesion: SessionData = Depends(requireAdminUser)):
    inst = inst_model.getInstalacionById(id_instalacion)
    if inst is None:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/instalaciones", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/instalaciones-detail.html",
        {"request": request, "inst": inst,
         "zonas": inst_model.getZonasByInstalacion(id_instalacion),
         "n_zonas": inst_model.countZonas(id_instalacion),
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_contexto_admin(sesion)})


# instalaciones — formulario de edición (solo Administrador)
def showEditInstalacionForm(request: Request,
                            id_instalacion: int,
                            id_sesion: UUID = Depends(session_cookie),
                            sesion: SessionData = Depends(requireAdminUser)):
    inst = inst_model.getInstalacionById(id_instalacion)
    if inst is None:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/instalaciones", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/instalaciones-edit.html",
        {"request": request, "inst": inst,
         "organizaciones": org_model.getAllOrganizations(solo_activas=True),
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_contexto_admin(sesion)})


# instalaciones — guarda los datos editados (solo Administrador)
def updateInstalacion(request: Request,
                      id_instalacion: int,
                      id_sesion: UUID = Depends(session_cookie),
                      sesion: SessionData = Depends(requireAdminUser),
                      nombre: str = Form(...),
                      descripcion: str = Form(""),
                      id_organizacion: str = Form(...),
                      calle: str = Form(...),
                      numero: str = Form(...),
                      ciudad: str = Form(...),
                      region: str = Form(...),
                      codigo_postal: str = Form("")):
    nombre = (nombre or "").strip()
    if not nombre:
        flashForm(request, "El nombre de la instalación es obligatorio.")
        return RedirectResponse(f"/admin/instalaciones/{id_instalacion}/edit", status_code=303)
    for campo in (calle, numero, ciudad, region):
        if not (campo or "").strip():
            flashForm(request, "La dirección completa es obligatoria (calle, número, ciudad y región).")
            return RedirectResponse(f"/admin/instalaciones/{id_instalacion}/edit", status_code=303)
    try:
        ok = inst_model.updateInstalacion(
            id_instalacion, nombre, (descripcion or "").strip() or None, int(id_organizacion),
            calle.strip(), numero.strip(), ciudad.strip(), region.strip(),
            (codigo_postal or "").strip() or None)
    except mysql.connector.Error as e:
        if e.errno in (1451, 1452):
            flashForm(request, "Organización inválida.")
        else:
            flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse(f"/admin/instalaciones/{id_instalacion}/edit", status_code=303)
    if not ok:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/instalaciones", status_code=303)
    flashForm(request, "Instalación actualizada correctamente.", ok=True)
    return RedirectResponse(f"/admin/instalaciones/{id_instalacion}", status_code=303)


# zonas — formulario de creación dentro de una instalación (solo Administrador)
def showCreateZonaForm(request: Request,
                       id_instalacion: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(requireAdminUser)):
    inst = inst_model.getInstalacionById(id_instalacion)
    if inst is None:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/instalaciones", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/zonas-create.html",
        {"request": request, "inst": inst,
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_contexto_admin(sesion)})


# zonas — guarda una zona nueva (solo Administrador)
def storeZona(request: Request,
              id_instalacion: int,
              id_sesion: UUID = Depends(session_cookie),
              sesion: SessionData = Depends(requireAdminUser),
              nombre: str = Form(...),
              descripcion: str = Form("")):
    if inst_model.getInstalacionById(id_instalacion) is None:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/instalaciones", status_code=303)
    nombre = (nombre or "").strip()
    if not nombre:
        flashForm(request, "El nombre de la zona es obligatorio.")
        return RedirectResponse(f"/admin/instalaciones/{id_instalacion}/zonas/create", status_code=303)
    try:
        zona_model.createZona(nombre, (descripcion or "").strip() or None, id_instalacion)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse(f"/admin/instalaciones/{id_instalacion}/zonas/create", status_code=303)
    flashForm(request, "Zona creada correctamente.", ok=True)
    return RedirectResponse(f"/admin/instalaciones/{id_instalacion}", status_code=303)


# zonas — detalle con sus dispositivos (solo Administrador)
def showZonaDetail(request: Request,
                   id_instalacion: int,
                   id_zona: int,
                   id_sesion: UUID = Depends(session_cookie),
                   sesion: SessionData = Depends(requireAdminUser)):
    zona = zona_model.getZonaById(id_zona)
    if zona is None or zona["id_instalacion"] != id_instalacion:
        flashForm(request, "La zona no existe.")
        return RedirectResponse(f"/admin/instalaciones/{id_instalacion}", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/zonas-detail.html",
        {"request": request, "zona": zona,
         "n_dispositivos": zona_model.countDevicesByZona(id_zona),
         "dispositivos": zona_model.getDevicesByZona(id_zona),
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_contexto_admin(sesion)})


# zonas — elimina solo si no tiene dispositivos (RESTRICT los protege)
def deleteZona(request: Request,
               id_instalacion: int,
               id_zona: int,
               id_sesion: UUID = Depends(session_cookie),
               sesion: SessionData = Depends(requireAdminUser)):
    if zona_model.countDevicesByZona(id_zona) > 0:
        flashForm(request, "No se puede eliminar: tiene dispositivos asociados.")
        return RedirectResponse(f"/admin/instalaciones/{id_instalacion}/zonas/{id_zona}", status_code=303)
    try:
        zona_model.deleteZona(id_zona)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al eliminar: {e.msg}")
        return RedirectResponse(f"/admin/instalaciones/{id_instalacion}/zonas/{id_zona}", status_code=303)
    flashForm(request, "Zona eliminada correctamente.", ok=True)
    return RedirectResponse(f"/admin/instalaciones/{id_instalacion}", status_code=303)


# instalaciones — elimina solo si no tiene zonas (CASCADE las borraría en silencio)
def deleteInstalacion(request: Request,
                      id_instalacion: int,
                      id_sesion: UUID = Depends(session_cookie),
                      sesion: SessionData = Depends(requireAdminUser)):
    if inst_model.countZonas(id_instalacion) > 0:
        flashForm(request, "No se puede eliminar: tiene zonas asociadas.")
        return RedirectResponse(f"/admin/instalaciones/{id_instalacion}", status_code=303)
    try:
        ok = inst_model.deleteInstalacion(id_instalacion)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al eliminar: {e.msg}")
        return RedirectResponse(f"/admin/instalaciones/{id_instalacion}", status_code=303)
    if not ok:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/instalaciones", status_code=303)
    flashForm(request, "Instalación eliminada correctamente.", ok=True)
    return RedirectResponse("/admin/instalaciones", status_code=303)
