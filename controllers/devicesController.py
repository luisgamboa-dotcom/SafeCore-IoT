"""Device detail page + admin devices CRUD."""
import time
from typing import Optional
from uuid import UUID

import mysql.connector
from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from config.sessionsConfig import SessionData, cookie as session_cookie, verificador, requireAdminUser
from models import devicesModel as dev_model
from models import zonesModel as zone_model
from models import usersModel as user_model
from utils import nodeIps
from utils.commonUtils import adminContext, restrictedOrganization, userSessionContext
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")


def showDeviceDetail(request: Request,
                     id_device: int,
                     id_sesion: UUID = Depends(session_cookie),
                     sesion: SessionData = Depends(verificador)):
    dev = dev_model.getDeviceDetail(id_device)
    if dev is None:
        return RedirectResponse("/dashboard", status_code=303)
    org = restrictedOrganization(sesion)
    if org is not None and dev.get("id_organizacion") != org:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "datos/device.html",
        {"request": request, "dev": dev, **userSessionContext(sesion)})


def _formContext(sesion, dev=None):
    return {"dev": dev,
            "zonas": zone_model.getAllZones(),
            "modelos": dev_model.getAllModels(),
            "estados": dev_model.getAllDeviceStates()}


def _haceCuanto(ts: float):
    """Etiqueta humana: '34 s', '5 min', '2 h', '3 d'."""
    s = max(1, int(time.time() - ts))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        return f"{s // 60} min"
    if s < 86400:
        return f"{s // 3600} h"
    return f"{s // 86400} d"


def showDevicesPage(request: Request,
                    id_sesion: UUID = Depends(session_cookie),
                    sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    dispositivos = dev_model.getAllDevices()
    # Ultima IP conocida de cada nodo (fichero data/nodo_ips.json): asi se
    # puede abrir la PWA de configuracion aunque el nodo cambie de red.
    for d in dispositivos:
        reg = nodeIps.obtener(d["codigo_serial"])
        if reg:
            d["ultima_ip"] = reg["ip"]
            d["ultima_ip_hace"] = _haceCuanto(reg["ts"])
        else:
            d["ultima_ip"] = None
            d["ultima_ip_hace"] = None
    return templates.TemplateResponse(request, "admin/devices.html",
        {"request": request, "dispositivos": dispositivos,
         "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def showCreateDeviceForm(request: Request,
                         id_sesion: UUID = Depends(session_cookie),
                         sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/devices-create.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok,
         **_formContext(sesion)})


def storeDevice(request: Request,
                id_sesion: UUID = Depends(session_cookie),
                sesion: SessionData = Depends(requireAdminUser),
                codigo_serial: str = Form(...),
                identificador_unico: str = Form(""),
                nombre: str = Form(...),
                firmware_version: str = Form(""),
                fecha_instalacion: str = Form(""),
                id_modelo: str = Form(...),
                id_estado_dispositivo: str = Form(...),
                id_zona: str = Form(...)):
    try:
        nuevo = dev_model.createDevice(
            codigo_serial.strip(), identificador_unico.strip() or None,
            nombre.strip(), firmware_version.strip() or None,
            fecha_instalacion or None, int(id_modelo),
            int(id_estado_dispositivo), int(id_zona))
    except mysql.connector.Error as e:
        if e.errno == 1062:
            campo = "código serial" if "codigo_serial" in (e.msg or "") else "identificador único"
            flashForm(request, f"Ya existe un dispositivo con ese {campo}.")
        else:
            flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse("/admin/devices/create", status_code=303)
    flashForm(request, "Dispositivo creado correctamente.", ok=True)
    return RedirectResponse(f"/admin/devices/{nuevo}/edit", status_code=303)


def showEditDeviceForm(request: Request,
                       id_device: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(requireAdminUser)):
    dev = dev_model.getDeviceDetail(id_device)
    if dev is None:
        flashForm(request, "El dispositivo no existe.")
        return RedirectResponse("/admin/devices", status_code=303)
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/devices-edit.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok,
         **_formContext(sesion, dev)})


def updateDeviceFromAdmin(request: Request,
                          id_device: int,
                          id_sesion: UUID = Depends(session_cookie),
                          sesion: SessionData = Depends(requireAdminUser),
                          codigo_serial: str = Form(...),
                          identificador_unico: str = Form(""),
                          nombre: str = Form(...),
                          firmware_version: str = Form(""),
                          fecha_instalacion: str = Form(""),
                          id_modelo: str = Form(...),
                          id_estado_dispositivo: str = Form(...),
                          id_zona: str = Form(...),
                          activo: str = Form("")):
    try:
        dev_model.updateDevice(
            id_device, codigo_serial.strip(), identificador_unico.strip() or None,
            nombre.strip(), firmware_version.strip() or None,
            fecha_instalacion or None, int(id_modelo),
            int(id_estado_dispositivo), int(id_zona), 1 if activo == "on" else 0)
    except mysql.connector.Error as e:
        if e.errno == 1062:
            campo = "código serial" if "codigo_serial" in (e.msg or "") else "identificador único"
            flashForm(request, f"Ya existe otro dispositivo con ese {campo}.")
        else:
            flashForm(request, f"Error al guardar: {e.msg}")
        return RedirectResponse(f"/admin/devices/{id_device}/edit", status_code=303)
    flashForm(request, "Dispositivo actualizado correctamente.", ok=True)
    return RedirectResponse("/admin/devices", status_code=303)


def deleteDeviceFromAdmin(request: Request,
                          id_device: int,
                          id_sesion: UUID = Depends(session_cookie),
                          sesion: SessionData = Depends(requireAdminUser)):
    try:
        dev_model.deleteDeviceCascade(id_device)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al eliminar: {e.msg}")
        return RedirectResponse(f"/admin/devices/{id_device}/edit", status_code=303)
    flashForm(request, "Dispositivo eliminado correctamente (incluyendo sus lecturas).", ok=True)
    return RedirectResponse("/admin/devices", status_code=303)
