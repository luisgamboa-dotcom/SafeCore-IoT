"""Admin zones management (nested under installations)."""
from uuid import UUID

import mysql.connector
from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from config.sessionsConfig import SessionData, cookie as session_cookie, requireAdminUser
from models import installationsModel as inst_model
from models import zonesModel as zone_model
from models import usersModel as user_model
from utils.commonUtils import adminContext
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")


def showCreateZoneForm(request: Request,
                       id_installation: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(requireAdminUser)):
    inst = inst_model.getInstallationById(id_installation)
    if inst is None:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/installations", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/zones-create.html",
        {"request": request, "inst": inst,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def storeZone(request: Request,
              id_installation: int,
              id_sesion: UUID = Depends(session_cookie),
              sesion: SessionData = Depends(requireAdminUser),
              nombre: str = Form(...),
              descripcion: str = Form("")):
    if inst_model.getInstallationById(id_installation) is None:
        flashForm(request, "La instalación no existe.")
        return RedirectResponse("/admin/installations", status_code=303)
    nombre = (nombre or "").strip()
    if not nombre:
        flashForm(request, "El nombre de la zona es obligatorio.")
        return RedirectResponse(f"/admin/installations/{id_installation}/zones/create", status_code=303)
    try:
        zone_model.createZone(nombre, (descripcion or "").strip() or None, id_installation)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse(f"/admin/installations/{id_installation}/zones/create", status_code=303)
    flashForm(request, "Zona creada correctamente.", ok=True)
    return RedirectResponse(f"/admin/installations/{id_installation}", status_code=303)


def showZoneDetail(request: Request,
                   id_installation: int,
                   id_zone: int,
                   id_sesion: UUID = Depends(session_cookie),
                   sesion: SessionData = Depends(requireAdminUser)):
    zona = zone_model.getZoneById(id_zone)
    if zona is None or zona["id_instalacion"] != id_installation:
        flashForm(request, "La zona no existe.")
        return RedirectResponse(f"/admin/installations/{id_installation}", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/zones-detail.html",
        {"request": request, "zona": zona,
         "n_dispositivos": zone_model.countDevicesByZone(id_zone),
         "dispositivos": zone_model.getDevicesByZone(id_zone),
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


# Device count precheck: fk_dev_zona is RESTRICT (and reglas_alerta→zonas is CASCADE).
def deleteZone(request: Request,
               id_installation: int,
               id_zone: int,
               id_sesion: UUID = Depends(session_cookie),
               sesion: SessionData = Depends(requireAdminUser)):
    if zone_model.countDevicesByZone(id_zone) > 0:
        flashForm(request, "No se puede eliminar: tiene dispositivos asociados.")
        return RedirectResponse(f"/admin/installations/{id_installation}/zones/{id_zone}", status_code=303)
    try:
        zone_model.deleteZone(id_zone)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al eliminar: {e.msg}")
        return RedirectResponse(f"/admin/installations/{id_installation}/zones/{id_zone}", status_code=303)
    flashForm(request, "Zona eliminada correctamente.", ok=True)
    return RedirectResponse(f"/admin/installations/{id_installation}", status_code=303)
