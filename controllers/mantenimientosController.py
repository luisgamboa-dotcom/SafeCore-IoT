from datetime import date, datetime
from uuid import UUID

from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse

from config.sessionsConfig import SessionData, cookie as session_cookie, verificador
from models import auditoriaModel as audit_model
from models import devicesModel as dev_model
from models import mantenimientosModel as mant_model
from models import usersModel as user_model
from utils.commonUtils import restrictedOrganization
from utils.flashUtils import flashForm


def puedeGestionar(sesion, dev):
    roles = user_model.getUserRoles(sesion.id_usuario)
    if "Administrador" in roles or "Superadmin" in roles:
        return True
    if "Supervisor" not in roles:
        return False
    org = restrictedOrganization(sesion)
    return org is not None and dev.get("id_organizacion") == org


def contextoFormulario(sesion, dev):
    org_dev = dev.get("id_organizacion")
    usuarios = (user_model.getUsersByOrganization(org_dev) if org_dev
                else user_model.getAllUsersBasic())
    activos = [u for u in usuarios if (u.get("estado") or "") == "Activo"]
    return {"tipos_mant": mant_model.getTiposMantenimiento(),
            "usuarios_mant": activos}


def _normalizarFecha(valor):
    limpio = (valor or "").strip().replace("T", " ")
    if not limpio:
        return None
    for formato in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(limpio, formato).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


def storeMantenimiento(request: Request,
                       id_device: int,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(verificador),
                       modo: str = Form("programado"),
                       id_tipo: str = Form(...),
                       id_responsable: str = Form(...),
                       fecha_programada: str = Form(""),
                       fecha_ejecucion: str = Form(""),
                       resultado: str = Form(""),
                       proxima_fecha: str = Form("")):
    dev = dev_model.getDeviceDetail(id_device)
    if dev is None:
        flashForm(request, "El dispositivo no existe.")
        return RedirectResponse("/dashboard", status_code=303)
    ficha = f"/dashboard/devices/{id_device}"
    if not puedeGestionar(sesion, dev):
        flashForm(request, "No tienes permisos para registrar mantenimientos de este dispositivo.")
        return RedirectResponse(ficha, status_code=303)
    modo = "realizado" if modo == "realizado" else "programado"
    fecha_hoy = date.today().isoformat()
    if not id_tipo.isdigit() or not id_responsable.isdigit():
        flashForm(request, "Datos inválidos: revisa el tipo y el responsable.")
        return RedirectResponse(ficha, status_code=303)
    try:
        if modo == "programado":
            fprog = _normalizarFecha(fecha_programada)
            if fprog is None or fprog[:10] < fecha_hoy:
                flashForm(request, "La fecha programada debe ser hoy o futura.")
                return RedirectResponse(ficha, status_code=303)
            nuevo = mant_model.createMantenimiento(
                id_device, int(id_tipo), fprog, int(id_responsable))
            detalle = f"programado, fecha {fprog}, responsable {id_responsable}"
            flashForm(request, "Mantenimiento programado correctamente.", ok=True)
        else:
            fejec = _normalizarFecha(fecha_ejecucion)
            proxima = _normalizarFecha(proxima_fecha)
            texto = (resultado or "").strip()
            if fejec is None or fejec[:10] > fecha_hoy:
                flashForm(request, "La fecha de ejecución debe ser hoy o anterior.")
                return RedirectResponse(ficha, status_code=303)
            if proxima is not None and proxima[:10] < fecha_hoy:
                flashForm(request, "La próxima fecha debe ser hoy o futura.")
                return RedirectResponse(ficha, status_code=303)
            if not texto:
                flashForm(request, "Indica el resultado del mantenimiento realizado.")
                return RedirectResponse(ficha, status_code=303)
            nuevo = mant_model.createMantenimiento(
                id_device, int(id_tipo), fejec, int(id_responsable),
                fecha_ejecucion=fejec, resultado=texto, proxima_fecha=proxima)
            detalle = (f"realizado, fecha {fejec}, resultado: {texto}, "
                       f"próxima {proxima or '-'}, responsable {id_responsable}")
            flashForm(request, "Mantenimiento registrado como realizado.", ok=True)
    except Exception as e:
        flashForm(request, f"Error al registrar el mantenimiento: {e}")
        return RedirectResponse(ficha, status_code=303)
    audit_model.registrarAuditoria(
        sesion.id_usuario, "mantenimiento", nuevo, "crear", "-",
        f"dispositivo {id_device}, tipo {id_tipo}, {detalle}")
    return RedirectResponse(ficha, status_code=303)


async def registrarEjecucion(request: Request,
                             id_mantenimiento: int,
                             id_sesion: UUID = Depends(session_cookie),
                             sesion: SessionData = Depends(verificador),
                             fecha_ejecucion: str = Form(...),
                             resultado: str = Form(...),
                             proxima_fecha: str = Form("")):
    mn = mant_model.getMantenimientoById(id_mantenimiento)
    if mn is None:
        flashForm(request, "El mantenimiento no existe.")
        return RedirectResponse("/dashboard", status_code=303)
    ficha = f"/dashboard/devices/{mn['id_dispositivo']}"
    dev = dev_model.getDeviceDetail(mn["id_dispositivo"])
    if dev is None or not puedeGestionar(sesion, dev):
        flashForm(request, "No tienes permisos para registrar la ejecución de este mantenimiento.")
        return RedirectResponse(ficha, status_code=303)
    if mn["estado"] != "programado":
        flashForm(request, "Ese mantenimiento ya fue ejecutado.")
        return RedirectResponse(ficha, status_code=303)
    fecha = _normalizarFecha(fecha_ejecucion)
    proxima = _normalizarFecha(proxima_fecha)
    texto = (resultado or "").strip()
    fecha_hoy = date.today().isoformat()
    if fecha is None or fecha[:10] > fecha_hoy:
        flashForm(request, "La fecha de ejecución debe ser hoy o anterior.")
        return RedirectResponse(ficha, status_code=303)
    if proxima is not None and proxima[:10] < fecha_hoy:
        flashForm(request, "La próxima fecha debe ser hoy o futura.")
        return RedirectResponse(ficha, status_code=303)
    if not texto:
        flashForm(request, "Datos inválidos: la fecha de ejecución y el resultado son obligatorios.")
        return RedirectResponse(ficha, status_code=303)
    try:
        mant_model.registrarEjecucion(id_mantenimiento, fecha, texto, proxima)
    except Exception as e:
        flashForm(request, f"Error al registrar la ejecución: {e}")
        return RedirectResponse(ficha, status_code=303)
    audit_model.registrarAuditoria(
        sesion.id_usuario, "mantenimiento", id_mantenimiento, "ejecutar",
        "estado: programado",
        f"estado: ejecutado, fecha {fecha}, resultado: {texto}, próxima {proxima or '-'}")
    flashForm(request, "Ejecución registrada correctamente.", ok=True)
    return RedirectResponse(ficha, status_code=303)
