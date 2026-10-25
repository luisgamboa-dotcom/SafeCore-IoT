"""My organization page: read-only view for members, edit for supervisors
and admins of their own organization. Deletion lives only in the admin panel."""
from uuid import UUID

import mysql.connector
from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessionsConfig import SessionData, cookie as session_cookie, verificador
from models import organizationsModel as org_model
from models import installationsModel as inst_model
from models import zonesModel as zone_model
from models import devicesModel as dev_model
from models import usersModel as user_model
from utils.commonUtils import restrictedOrganization
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")


def _puedeEditar(roles):
    return bool({"Supervisor", "Administrador", "Superadmin"} & set(roles))


def _orgAccesible(sesion, org_param=None):
    """Organizacion a mostrar. Solo el Superadmin puede abrir una distinta de la suya."""
    roles = user_model.getUserRoles(sesion.id_usuario)
    es_super = "Superadmin" in roles
    user = user_model.getUserById(sesion.id_usuario)
    if es_super and org_param and str(org_param).strip().isdigit():
        return int(org_param), True, _puedeEditar(roles)
    return user["id_organizacion"], es_super, _puedeEditar(roles)


def showMyOrganization(request: Request,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(verificador),
                       org: str = ""):
    id_org, _, puede_editar = _orgAccesible(sesion, org)
    if id_org is None:
        flashForm(request, "No tienes una organización asignada.")
        return RedirectResponse("/dashboard", status_code=303)
    org = org_model.getOrganizationById(id_org)
    if org is None:
        flashForm(request, "La organización no existe.")
        return RedirectResponse("/dashboard", status_code=303)
    restricciones = restrictedOrganization(sesion)
    instalaciones = []
    for inst in inst_model.getInstallationsByOrganization(id_org):
        zonas = []
        for zona in inst_model.getZonesByInstallation(inst["id_instalacion"]):
            dispositivos = zone_model.getDevicesByZone(zona["id_zona"])
            zonas.append({"zona": zona, "dispositivos": dispositivos})
        instalaciones.append({"instalacion": inst, "zonas": zonas})
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "myOrganization/index.html",
        {"request": request, "org": org, "instalaciones": instalaciones,
         "usuarios": user_model.getUsersByOrganization(id_org),
         "puede_editar": puede_editar, "flash_msg": flash_msg,
         "flash_ok": flash_ok,
         "id_mi_org": user_model.getUserById(sesion.id_usuario)["id_organizacion"],
         **_sesionCtx(sesion)})


def _sesionCtx(sesion):
    from utils.commonUtils import adminContext, userSessionContext
    return {**adminContext(sesion, user_model.getUserById(sesion.id_usuario)),
            "id_usuario": sesion.id_usuario}


def _guardInstalacion(id_instalacion, id_org):
    inst = inst_model.getInstallationById(id_instalacion)
    return inst if (inst is not None and inst["id_organizacion"] == id_org) else None


def _guardZona(id_zona, id_org):
    zona = zone_model.getZoneById(id_zona)
    if zona is None:
        return None
    return zona if _guardInstalacion(zona["id_instalacion"], id_org) else None


def showEditMyOrganization(request: Request,
                           id_sesion: UUID = Depends(session_cookie),
                           sesion: SessionData = Depends(verificador),
                           org: str = ""):
    id_org, _, puede_editar = _orgAccesible(sesion, org)
    if id_org is None or not puede_editar:
        flashForm(request, "No tienes permiso para editar esa organización.")
        return RedirectResponse("/mi-organizacion", status_code=303)
    org = org_model.getOrganizationById(id_org)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "myOrganization/edit.html",
        {"request": request, "org": org, "flash_msg": flash_msg,
         "flash_ok": flash_ok, **_sesionCtx(sesion)})


def updateMyOrganization(request: Request,
                         id_sesion: UUID = Depends(session_cookie),
                         sesion: SessionData = Depends(verificador),
                         nombre: str = Form(...),
                         descripcion: str = Form("")):
    id_org, _, puede_editar = _orgAccesible(sesion)
    if id_org is None or not puede_editar:
        flashForm(request, "No tienes permiso para editar esa organización.")
        return RedirectResponse("/mi-organizacion", status_code=303)
    if not (nombre or "").strip():
        flashForm(request, "El nombre de la organización es obligatorio.")
        return RedirectResponse("/mi-organizacion/editar", status_code=303)
    org_model.updateOrganization(id_org, nombre.strip(), (descripcion or "").strip() or None)
    flashForm(request, "Organización actualizada correctamente.", ok=True)
    return RedirectResponse("/mi-organizacion", status_code=303)


def showCreateInstallationForm(request: Request,
                               id_sesion: UUID = Depends(session_cookie),
                               sesion: SessionData = Depends(verificador)):
    id_org, _, puede_editar = _orgAccesible(sesion)
    if id_org is None or not puede_editar:
        flashForm(request, "No tienes permiso para crear instalaciones.")
        return RedirectResponse("/mi-organizacion", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "myOrganization/installations-create.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok,
         **_sesionCtx(sesion)})


def storeInstallation(request: Request,
                      id_sesion: UUID = Depends(session_cookie),
                      sesion: SessionData = Depends(verificador),
                      nombre: str = Form(...),
                      descripcion: str = Form(""),
                      calle: str = Form(...),
                      numero: str = Form(...),
                      ciudad: str = Form(...),
                      region: str = Form(...),
                      codigo_postal: str = Form("")):
    id_org, _, puede_editar = _orgAccesible(sesion)
    if id_org is None or not puede_editar:
        flashForm(request, "No tienes permiso para crear instalaciones.")
        return RedirectResponse("/mi-organizacion", status_code=303)
    if not (nombre or "").strip():
        flashForm(request, "El nombre de la instalación es obligatorio.")
        return RedirectResponse("/mi-organizacion/installations/create", status_code=303)
    for campo in (calle, numero, ciudad, region):
        if not (campo or "").strip():
            flashForm(request, "La dirección completa es obligatoria (calle, número, ciudad y región).")
            return RedirectResponse("/mi-organizacion/installations/create", status_code=303)
    try:
        inst_model.createInstallation(
            nombre.strip(), (descripcion or "").strip() or None, id_org,
            calle.strip(), numero.strip(), ciudad.strip(), region.strip(),
            (codigo_postal or "").strip() or None)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse("/mi-organizacion/installations/create", status_code=303)
    flashForm(request, "Instalación creada correctamente.", ok=True)
    return RedirectResponse("/mi-organizacion", status_code=303)


def showEditInstallationForm(request: Request,
                             id_installation: int,
                             id_sesion: UUID = Depends(session_cookie),
                             sesion: SessionData = Depends(verificador)):
    id_org, _, puede_editar = _orgAccesible(sesion)
    inst = _guardInstalacion(id_installation, id_org) if id_org else None
    if inst is None or not puede_editar:
        flashForm(request, "Esa instalación no es de tu organización o no tienes permiso.")
        return RedirectResponse("/mi-organizacion", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "myOrganization/installations-edit.html",
        {"request": request, "inst": inst,
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_sesionCtx(sesion)})


def updateInstallation(request: Request,
                       id_installation: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(verificador),
                       nombre: str = Form(...),
                       descripcion: str = Form(""),
                       calle: str = Form(...),
                       numero: str = Form(...),
                       ciudad: str = Form(...),
                       region: str = Form(...),
                       codigo_postal: str = Form("")):
    id_org, _, puede_editar = _orgAccesible(sesion)
    inst = _guardInstalacion(id_installation, id_org) if id_org else None
    if inst is None or not puede_editar:
        flashForm(request, "Esa instalación no es de tu organización o no tienes permiso.")
        return RedirectResponse("/mi-organizacion", status_code=303)
    if not (nombre or "").strip():
        flashForm(request, "El nombre de la instalación es obligatorio.")
        return RedirectResponse(f"/mi-organizacion/installations/{id_installation}/editar", status_code=303)
    inst_model.updateInstallation(
        id_installation, nombre.strip(), (descripcion or "").strip() or None, id_org,
        calle.strip(), numero.strip(), ciudad.strip(), region.strip(),
        (codigo_postal or "").strip() or None)
    flashForm(request, "Instalación actualizada correctamente.", ok=True)
    return RedirectResponse("/mi-organizacion", status_code=303)


def showCreateZoneForm(request: Request,
                       id_installation: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(verificador)):
    id_org, _, puede_editar = _orgAccesible(sesion)
    inst = _guardInstalacion(id_installation, id_org) if id_org else None
    if inst is None or not puede_editar:
        flashForm(request, "Esa instalación no es de tu organización o no tienes permiso.")
        return RedirectResponse("/mi-organizacion", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "myOrganization/zones-create.html",
        {"request": request, "inst": inst, "flash_msg": flash_msg,
         "flash_ok": flash_ok, **_sesionCtx(sesion)})


def storeZone(request: Request,
              id_installation: int,
              id_sesion: UUID = Depends(session_cookie),
              sesion: SessionData = Depends(verificador),
              nombre: str = Form(...),
              descripcion: str = Form("")):
    id_org, _, puede_editar = _orgAccesible(sesion)
    inst = _guardInstalacion(id_installation, id_org) if id_org else None
    if inst is None or not puede_editar:
        flashForm(request, "Esa instalación no es de tu organización o no tienes permiso.")
        return RedirectResponse("/mi-organizacion", status_code=303)
    if not (nombre or "").strip():
        flashForm(request, "El nombre de la zona es obligatorio.")
        return RedirectResponse(f"/mi-organizacion/installations/{id_installation}/zones/create", status_code=303)
    zone_model.createZone(nombre.strip(), (descripcion or "").strip() or None, id_installation)
    flashForm(request, "Zona creada correctamente.", ok=True)
    return RedirectResponse("/mi-organizacion", status_code=303)


def showEditZoneForm(request: Request,
                     id_zone: int,
                     id_sesion: UUID = Depends(session_cookie),
                     sesion: SessionData = Depends(verificador)):
    id_org, _, puede_editar = _orgAccesible(sesion)
    zona = _guardZona(id_zone, id_org) if id_org else None
    if zona is None or not puede_editar:
        flashForm(request, "Esa zona no es de tu organización o no tienes permiso.")
        return RedirectResponse("/mi-organizacion", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "myOrganization/zones-edit.html",
        {"request": request, "zona": zona,
         "inst": inst_model.getInstallationById(zona["id_instalacion"]),
         "flash_msg": flash_msg, "flash_ok": flash_ok, **_sesionCtx(sesion)})


def updateZone(request: Request,
               id_zone: int,
               id_sesion: UUID = Depends(session_cookie),
               sesion: SessionData = Depends(verificador),
               nombre: str = Form(...),
               descripcion: str = Form("")):
    id_org, _, puede_editar = _orgAccesible(sesion)
    zona = _guardZona(id_zone, id_org) if id_org else None
    if zona is None or not puede_editar:
        flashForm(request, "Esa zona no es de tu organización o no tienes permiso.")
        return RedirectResponse("/mi-organizacion", status_code=303)
    if not (nombre or "").strip():
        flashForm(request, "El nombre de la zona es obligatorio.")
        return RedirectResponse(f"/mi-organizacion/zones/{id_zone}/editar", status_code=303)
    zone_model.updateZone(id_zone, nombre.strip(), (descripcion or "").strip() or None)
    flashForm(request, "Zona actualizada correctamente.", ok=True)
    return RedirectResponse("/mi-organizacion", status_code=303)
