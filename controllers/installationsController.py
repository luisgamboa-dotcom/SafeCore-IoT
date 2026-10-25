"""Admin installations management (address handled inline)."""
from uuid import UUID

import mysql.connector
from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from config.sessionsConfig import SessionData, cookie as session_cookie, requireAdminUser
from models import installationsModel as inst_model
from models import organizationsModel as org_model
from models import usersModel as user_model
from utils.commonUtils import adminContext
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")


def showInstallationsPage(request: Request,
                          id_sesion: UUID = Depends(session_cookie),
                          sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/installations.html",
        {"request": request, "instalaciones": inst_model.getAllInstallations(),
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def showCreateInstallationForm(request: Request,
                               id_sesion: UUID = Depends(session_cookie),
                               sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/installations-create.html",
        {"request": request, "organizaciones": org_model.getAllOrganizations(solo_activas=True),
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def storeInstallation(request: Request,
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
        return RedirectResponse("/admin/installations/create", status_code=303)
    for campo in (calle, numero, ciudad, region):
        if not (campo or "").strip():
            flashForm(request, "La dirección completa es obligatoria (calle, número, ciudad y región).")
            return RedirectResponse("/admin/installations/create", status_code=303)
    try:
        inst_model.createInstallation(
            nombre, (descripcion or "").strip() or None, int(id_organizacion),
            calle.strip(), numero.strip(), ciudad.strip(), region.strip(),
            (codigo_postal or "").strip() or None)
    except mysql.connector.Error as e:
        if e.errno in (1451, 1452):
            flashForm(request, "Organización inválida.")
        else:
            flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse("/admin/installations/create", status_code=303)
    flashForm(request, "Instalación creada correctamente.", ok=True)
    return RedirectResponse("/admin/installations", status_code=303)


def showInstallationDetail(request: Request,
                           id_installation: int,
                           id_sesion: UUID = Depends(session_cookie),
                           sesion: SessionData = Depends(requireAdminUser)):
    inst = inst_model.getInstallationById(id_installation)
    if inst is None:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/installations", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/installations-detail.html",
        {"request": request, "inst": inst,
         "zonas": inst_model.getZonesByInstallation(id_installation),
         "n_zonas": inst_model.countZones(id_installation),
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def showEditInstallationForm(request: Request,
                             id_installation: int,
                             id_sesion: UUID = Depends(session_cookie),
                             sesion: SessionData = Depends(requireAdminUser)):
    inst = inst_model.getInstallationById(id_installation)
    if inst is None:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/installations", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/installations-edit.html",
        {"request": request, "inst": inst,
         "organizaciones": org_model.getAllOrganizations(solo_activas=True),
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def updateInstallation(request: Request,
                       id_installation: int,
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
        return RedirectResponse(f"/admin/installations/{id_installation}/edit", status_code=303)
    for campo in (calle, numero, ciudad, region):
        if not (campo or "").strip():
            flashForm(request, "La dirección completa es obligatoria (calle, número, ciudad y región).")
            return RedirectResponse(f"/admin/installations/{id_installation}/edit", status_code=303)
    try:
        ok = inst_model.updateInstallation(
            id_installation, nombre, (descripcion or "").strip() or None, int(id_organizacion),
            calle.strip(), numero.strip(), ciudad.strip(), region.strip(),
            (codigo_postal or "").strip() or None)
    except mysql.connector.Error as e:
        if e.errno in (1451, 1452):
            flashForm(request, "Organización inválida.")
        else:
            flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse(f"/admin/installations/{id_installation}/edit", status_code=303)
    if not ok:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/installations", status_code=303)
    flashForm(request, "Instalación actualizada correctamente.", ok=True)
    return RedirectResponse(f"/admin/installations/{id_installation}", status_code=303)


def deleteInstallation(request: Request,
                       id_installation: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(requireAdminUser)):
    try:
        ok = inst_model.forceDeleteInstallation(id_installation)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al eliminar: {e.msg}")
        return RedirectResponse(f"/admin/installations/{id_installation}", status_code=303)
    if not ok:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/installations", status_code=303)
    flashForm(request, "Instalación eliminada correctamente (incluyendo sus zonas y dispositivos).", ok=True)
    return RedirectResponse("/admin/installations", status_code=303)
