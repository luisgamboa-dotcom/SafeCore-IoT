"""Ficha de dispositivo y CRUD de dispositivos del panel admin."""
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
from models import auditoriaModel as audit_model
from models import alertsModel as alerts_model
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
    contexto = {"request": request, "dev": dev, **userSessionContext(sesion)}
    if contexto["is_admin"]:
        from models import rulesModel
        try:
            contexto["reglas"] = rulesModel.getZoneRules(dev["id_zona"])
            contexto["magnitudes"] = rulesModel.getMagnitudes()
        except Exception:
            contexto["reglas"] = []
            contexto["magnitudes"] = []
        try:
            contexto["sensores_form"] = dev_model.getSensoresOfDevice(id_device)
            contexto["dev_tiene_lecturas"] = dev_model.tieneLecturas(id_device)
            contexto["modelos_form"] = dev_model.getAllModels()
        except Exception:
            contexto["sensores_form"] = []
            contexto["dev_tiene_lecturas"] = False
            contexto["modelos_form"] = []
    try:
        from models import alertsModel
        contexto["alertas"] = alertsModel.getDeviceAlertas(id_device)
    except Exception:
        contexto["alertas"] = []
    try:
        from models import mantenimientosModel as mant_model
        contexto["mantenimientos"] = mant_model.getMantenimientosByDevice(id_device)
        contexto["ultimo_mant"] = mant_model.getUltimoMantenimiento(id_device)
    except Exception:
        contexto["mantenimientos"] = []
        contexto["ultimo_mant"] = None
    contexto["flash_msg"], _, contexto["flash_ok"] = popFormFlash(request)
    return templates.TemplateResponse(
        request, "datos/device.html", contexto)


def _formContext(sesion, dev=None):
    ctx = {"dev": dev,
           "zonas": zone_model.getAllZones(),
           "modelos": dev_model.getAllModels()}
    if dev is not None:
        try:
            ctx["sensores"] = dev_model.getSensoresOfDevice(dev["id_dispositivo"])
            ctx["dev_tiene_lecturas"] = dev_model.tieneLecturas(dev["id_dispositivo"])
        except Exception:
            ctx["sensores"] = []
            ctx["dev_tiene_lecturas"] = False
    return ctx


MSG_MODELO_BLOQUEADO = ("El modelo no puede cambiar si existe historial; "
                        "registre un equipo nuevo")


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
                id_zona: str = Form(...)):
    try:
        nuevo = dev_model.createDevice(
            codigo_serial.strip(), identificador_unico.strip() or None,
            nombre.strip(), firmware_version.strip() or None,
            fecha_instalacion or None, int(id_modelo), int(id_zona))
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


async def updateDeviceFromAdmin(request: Request,
                                id_device: int,
                                id_sesion: UUID = Depends(session_cookie),
                                sesion: SessionData = Depends(requireAdminUser),
                                codigo_serial: str = Form(...),
                                identificador_unico: str = Form(""),
                                nombre: str = Form(...),
                                firmware_version: str = Form(""),
                                notas: str = Form(""),
                                fecha_instalacion: str = Form(""),
                                id_modelo: str = Form(...),
                                id_zona: str = Form(...),
                                activo: str = Form("")):
    dev = dev_model.getDeviceDetail(id_device)
    if dev is None:
        flashForm(request, "El dispositivo no existe.")
        return RedirectResponse("/admin/devices", status_code=303)
    form = await request.form()
    destino = form.get("origen", "admin")
    volver_ficha = f"/dashboard/devices/{id_device}"
    volver_admin = f"/admin/devices/{id_device}/edit"

    def volver():
        return RedirectResponse(volver_ficha if destino == "ficha" else volver_admin,
                                status_code=303)

    # HU-015: el modelo no puede cambiar si el dispositivo tiene historial de lecturas.
    if int(id_modelo) != dev["id_modelo"] and dev_model.tieneLecturas(id_device):
        flashForm(request, MSG_MODELO_BLOQUEADO)
        return volver()

    # Las frecuencias llegan dinámicamente como campos frec_<id_sensor> del formulario.
    frecuencias = []
    for clave, valor in form.items():
        if not clave.startswith("frec_"):
            continue
        id_sensor = clave[5:]
        if not id_sensor.isdigit() or not str(valor).strip().isdigit() \
                or int(valor) < 1:
            flashForm(request, "Valores inválidos: frecuencia de muestreo no"
                               " válida (entero positivo).")
            return volver()
        frecuencias.append((int(id_sensor), int(valor)))

    cambio_audit = [('codigo_serial', dev["codigo_serial"], codigo_serial.strip()),
                    ('identificador_unico', dev["identificador_unico"],
                     identificador_unico.strip() or None),
                    ('nombre', dev["nombre"], nombre.strip()),
                    ('firmware_version', dev["firmware_version"],
                     firmware_version.strip() or None),
                    ('notas', dev.get("notas"), (notas or "").strip() or None),
                    ('fecha_instalacion', dev["fecha_instalacion"],
                     fecha_instalacion or None),
                    ('id_modelo', dev["id_modelo"], int(id_modelo)),
                    ('id_zona', dev["id_zona"], int(id_zona)),
                    ('activo', 1 if dev["activo"] else 0, 1 if activo == "on" else 0)]

    try:
        dev_model.updateDevice(
            id_device, codigo_serial.strip(), identificador_unico.strip() or None,
            nombre.strip(), firmware_version.strip() or None,
            (notas or "").strip() or None,
            fecha_instalacion or None, int(id_modelo),
            dev["id_estado_dispositivo"], int(id_zona),
            1 if activo == "on" else 0)
    except mysql.connector.Error as e:
        if e.errno == 1062:
            campo = "código serial" if "codigo_serial" in (e.msg or "") else "identificador único"
            flashForm(request, f"Ya existe otro dispositivo con ese {campo}.")
        else:
            flashForm(request, f"Error al guardar: {e.msg}")
        return volver()

    # Auditar cada cambio de frecuencia (el valor anterior se lee antes de actualizar).
    try:
        anteriores = {s["id_sensor"]: s["frecuencia_muestreo"]
                      for s in dev_model.getSensoresOfDevice(id_device)}
        for id_sensor, frecuencia in frecuencias:
            dev_model.updateSensorFrecuencia(id_sensor, frecuencia)
            if anteriores.get(id_sensor) != frecuencia:
                audit_model.registrarAuditoria(
                    sesion.id_usuario, "dispositivo", id_device, "frecuencia",
                    f"sensor {id_sensor}: {anteriores.get(id_sensor)}",
                    f"sensor {id_sensor}: {frecuencia}")
    except mysql.connector.Error as e:
        flashForm(request, f"Error al actualizar frecuencias: {e.msg}")
        return volver()

    # Criterio 1 de HU-015: auditar cada campo modificado con su valor anterior y nuevo.
    for campo, anterior, nuevo in cambio_audit:
        if campo == "fecha_instalacion":
            # Form sends YYYY-MM-DD; DB keeps full timestamp. Compare by date.
            a = anterior.strftime("%Y-%m-%d") if anterior else ""
            n = (str(nuevo or "").strip())[:10]
            if a == n:
                continue
        elif (anterior if anterior is not None else "") == (nuevo if nuevo is not None else ""):
            continue
        audit_model.registrarAuditoria(sesion.id_usuario, "dispositivo",
                                       id_device, "update",
                                       f"{campo}: {anterior}",
                                       f"{campo}: {nuevo}")
    flashForm(request, "Dispositivo actualizado correctamente.", ok=True)
    return volver()


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


async def toggleDeviceActive(request: Request,
                             id_device: int,
                             id_sesion: UUID = Depends(session_cookie),
                             sesion: SessionData = Depends(requireAdminUser),
                             motivo: str = Form("")):
    """HU-014: da de baja (o reactiva) un dispositivo sin eliminar su informacion.
    Al desactivar cancela sus alertas activas y audita quien, cuando y con que motivo."""
    dev = dev_model.getDeviceDetail(id_device)
    if dev is None:
        flashForm(request, "El dispositivo no existe.")
        return RedirectResponse("/admin/devices", status_code=303)

    # Origen del envio (lista admin o ficha del dashboard) para volver al lugar.
    form = await request.form()
    destino = form.get("origen", "admin")
    def volver():
        return RedirectResponse(
            f"/dashboard/devices/{id_device}" if destino == "ficha"
            else "/admin/devices", status_code=303)

    try:
        if dev["activo"]:
            dev_model.setDeviceActivo(id_device, False)
            canceladas = alerts_model.cancelarAlertasDeDispositivo(id_device)
            # Auditoria: cambio de bandera + motivo opcional del administrador.
            audit_model.registrarAuditoria(sesion.id_usuario, "dispositivo",
                                           id_device, "desactivar",
                                           "activo: 1", "activo: 0")
            motivo_limpio = (motivo or "").strip()
            if motivo_limpio:
                audit_model.registrarAuditoria(sesion.id_usuario, "dispositivo",
                                               id_device, "desactivar",
                                               "motivo: -", f"motivo: {motivo_limpio}")
            flashForm(request,
                      f"Dispositivo desactivado: se conservó su historial y se "
                      f"cancelaron {canceladas} alerta(s) activa(s).", ok=True)
        else:
            dev_model.setDeviceActivo(id_device, True)
            audit_model.registrarAuditoria(sesion.id_usuario, "dispositivo",
                                           id_device, "activar",
                                           "activo: 0", "activo: 1")
            flashForm(request, "Dispositivo activado correctamente.", ok=True)
    except mysql.connector.Error as e:
        flashForm(request, f"Error al guardar el estado del dispositivo: {e.msg}")
        return volver()
    return volver()
