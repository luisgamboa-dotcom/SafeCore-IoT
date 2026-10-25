"""Admin organizations management."""
from uuid import UUID

import mysql.connector
from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from config.sessionsConfig import SessionData, cookie as session_cookie, requireAdminUser
from models import organizationsModel as org_model
from models import usersModel as user_model
from utils.commonUtils import adminContext
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")


def showOrganizationsPage(request: Request,
                          id_sesion: UUID = Depends(session_cookie),
                          sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/organizations.html",
        {"request": request, "organizaciones": org_model.getAllOrganizations(),
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def showCreateOrganizationForm(request: Request,
                               id_sesion: UUID = Depends(session_cookie),
                               sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/organizations-create.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


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


def showOrganizationDetail(request: Request,
                           id_organization: int,
                           id_sesion: UUID = Depends(session_cookie),
                           sesion: SessionData = Depends(requireAdminUser)):
    org = org_model.getOrganizationById(id_organization)
    if org is None:
        flashForm(request, "La organización no existe.")
        return RedirectResponse("/admin/organizations", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/organizations-detail.html",
        {"request": request, "org": org,
         "tiene_relaciones": org_model.countOrganizationRelations(id_organization) > 0,
         "miembros": user_model.getUsersByOrganization(id_organization),
         "candidatos": user_model.getUsersOutsideOrganization(id_organization),
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def showEditOrganizationForm(request: Request,
                             id_organization: int,
                             id_sesion: UUID = Depends(session_cookie),
                             sesion: SessionData = Depends(requireAdminUser)):
    org = org_model.getOrganizationById(id_organization)
    if org is None:
        flashForm(request, "La organización no existe.")
        return RedirectResponse("/admin/organizations", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/organizations-edit.html",
        {"request": request, "org": org,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def updateOrganization(request: Request,
                       id_organization: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(requireAdminUser),
                       nombre: str = Form(...),
                       descripcion: str = Form("")):
    nombre = (nombre or "").strip()
    if not nombre:
        flashForm(request, "El nombre de la organización es obligatorio.")
        return RedirectResponse(f"/admin/organizations/{id_organization}/edit", status_code=303)
    try:
        org_model.updateOrganization(id_organization, nombre, (descripcion or "").strip() or None)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse(f"/admin/organizations/{id_organization}/edit", status_code=303)
    flashForm(request, "Organización actualizada correctamente.", ok=True)
    return RedirectResponse(f"/admin/organizations/{id_organization}", status_code=303)


# Block if there are relations: deactivate instead (has users or installations).
def deleteOrganization(request: Request,
                       id_organization: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(requireAdminUser)):
    try:
        org_model.forceDeleteOrganization(id_organization)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al eliminar: {e.msg}")
        return RedirectResponse(f"/admin/organizations/{id_organization}", status_code=303)
    flashForm(request, "Organización eliminada correctamente (incluyendo sus instalaciones).", ok=True)
    return RedirectResponse("/admin/organizations", status_code=303)


def removeUserFromOrganization(request: Request,
                               id_organization: int,
                               id_sesion: UUID = Depends(session_cookie),
                               sesion: SessionData = Depends(requireAdminUser),
                               id_usuario: int = Form(...)):
    user_model.setUserOrganization(id_usuario, None)
    flashForm(request, "Usuario quitado de la organización.", ok=True)
    return RedirectResponse(f"/admin/organizations/{id_organization}", status_code=303)


def addUserToOrganization(request: Request,
                          id_organization: int,
                          id_sesion: UUID = Depends(session_cookie),
                          sesion: SessionData = Depends(requireAdminUser),
                          id_usuario: int = Form(...)):
    if org_model.getOrganizationById(id_organization) is None:
        flashForm(request, "La organización no existe.")
        return RedirectResponse("/admin/organizations", status_code=303)
    user_model.setUserOrganization(id_usuario, id_organization)
    flashForm(request, "Usuario agregado a la organización.", ok=True)
    return RedirectResponse(f"/admin/organizations/{id_organization}", status_code=303)
