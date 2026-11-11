"""Suscripciones Gratuito/Premium: activacion del plan por organizacion.

Sin pasarela real todavia: el boton "Mejorar plan" deriva a un placeholder
de Webpay (/templates/webpay/pago.html) donde el pago aun no ocurre; solo
existe un boton de demostracion que activa el plan para poder mostrar ambos
estados del sistema.
"""
from uuid import UUID

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessionsConfig import SessionData, cookie as session_cookie, verificador
from models import organizationsModel as org_model
from utils.commonUtils import userSessionContext, esOrganizacionPremium
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")

PRECIO_PREMIUM = "6.000"
PRECIO_PREMIUM_CLP = 6000


def _contexto(request, sesion):
    flash_msg, old, flash_ok = popFormFlash(request)
    return {"flash_msg": flash_msg, "flash_ok": flash_ok,
            **userSessionContext(sesion)}


def _orgDelUsuario(sesion: SessionData):
    from models import usersModel as user_model
    usuario = user_model.getUserById(sesion.id_usuario)
    if usuario is None or usuario["id_organizacion"] is None:
        return None
    return usuario["id_organizacion"]


def mejorarPlan(request: Request,
                id_sesion: UUID = Depends(session_cookie),
                sesion: SessionData = Depends(verificador)):
    """Deriva a la pasarela Webpay (placeholder sin pago real)."""
    if _orgDelUsuario(sesion) is None:
        flashForm(request, "Necesitas pertenecer a una organización para "
                           "contratar un plan.")
        return RedirectResponse("/users/perfil", status_code=303)
    if esOrganizacionPremium(sesion):
        flashForm(request, "Tu organización ya tiene el plan Premium.", ok=True)
        return RedirectResponse("/users/perfil", status_code=303)
    return RedirectResponse("/webpay/pago", status_code=303)


def showWebpayPago(request: Request,
                   id_sesion: UUID = Depends(session_cookie),
                   sesion: SessionData = Depends(verificador)):
    id_org = _orgDelUsuario(sesion)
    if id_org is None:
        flashForm(request, "Necesitas pertenecer a una organización para "
                           "contratar un plan.")
        return RedirectResponse("/users/perfil", status_code=303)
    if esOrganizacionPremium(sesion):
        flashForm(request, "Tu organización ya tiene el plan Premium.", ok=True)
        return RedirectResponse("/users/perfil", status_code=303)
    org = org_model.getOrganizationById(id_org)
    return templates.TemplateResponse(
        request, "webpay/pago.html",
        {"request": request, "organizacion": org,
         "precio": PRECIO_PREMIUM,
         **_contexto(request, sesion)})


async def pagoSimulado(request: Request,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(verificador)):
    """Demo: activa el plan Premium sin pasarela real (pago no disponible)."""
    id_org = _orgDelUsuario(sesion)
    if id_org is None:
        flashForm(request, "Necesitas pertenecer a una organización para "
                           "contratar un plan.")
        return RedirectResponse("/users/perfil", status_code=303)
    org_model.setPlanOrganizacion(id_org, True)
    flashForm(request, "Pago simulado (demo) aceptado: plan Premium activado "
                       "para tu organización.", ok=True)
    return RedirectResponse("/users/perfil", status_code=303)


async def bajarPlan(request: Request,
                    id_sesion: UUID = Depends(session_cookie),
                    sesion: SessionData = Depends(verificador)):
    """Vuelve al plan Gratuito (para demostrar ambos estados)."""
    id_org = _orgDelUsuario(sesion)
    if id_org is None:
        flashForm(request, "Necesitas pertenecer a una organización para "
                           "cambiar de plan.")
        return RedirectResponse("/users/perfil", status_code=303)
    org_model.setPlanOrganizacion(id_org, False)
    flashForm(request, "Tu organización volvió al plan Gratuito.", ok=True)
    return RedirectResponse("/users/perfil", status_code=303)
