"""Suscripciones Gratuito/Premium: activacion del plan por usuario.

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
from models import usersModel as user_model
from utils.commonUtils import userSessionContext, esUsuarioPremium
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")

PRECIO_PREMIUM = "6.000"
PRECIO_PREMIUM_CLP = 6000


def _contexto(request, sesion):
    flash_msg, old, flash_ok = popFormFlash(request)
    return {"flash_msg": flash_msg, "flash_ok": flash_ok,
            **userSessionContext(sesion)}


def _usuarioDeSesion(sesion: SessionData):
    return user_model.getUserById(sesion.id_usuario)


def mejorarPlan(request: Request,
                id_sesion: UUID = Depends(session_cookie),
                sesion: SessionData = Depends(verificador)):
    """Deriva a la pasarela Webpay (placeholder sin pago real)."""
    usuario = _usuarioDeSesion(sesion)
    if usuario is None:
        flashForm(request, "No se encontro tu cuenta: inicia sesion "
                           "nuevamente.")
        return RedirectResponse("/users/login", status_code=303)
    if esUsuarioPremium(sesion):
        flashForm(request, "Tu cuenta ya tiene el plan Premium.", ok=True)
        return RedirectResponse("/users/perfil", status_code=303)
    return RedirectResponse("/webpay/pago", status_code=303)


def showWebpayPago(request: Request,
                   id_sesion: UUID = Depends(session_cookie),
                   sesion: SessionData = Depends(verificador)):
    usuario = _usuarioDeSesion(sesion)
    if usuario is None:
        flashForm(request, "No se encontro tu cuenta: inicia sesion "
                           "nuevamente.")
        return RedirectResponse("/users/login", status_code=303)
    if esUsuarioPremium(sesion):
        flashForm(request, "Tu cuenta ya tiene el plan Premium.", ok=True)
        return RedirectResponse("/users/perfil", status_code=303)
    return templates.TemplateResponse(
        request, "webpay/pago.html",
        {"request": request, "usuario": usuario,
         "precio": PRECIO_PREMIUM,
         **_contexto(request, sesion)})


async def pagoSimulado(request: Request,
                       id_sesion: UUID = Depends(session_cookie),
                       sesion: SessionData = Depends(verificador)):
    """Demo: activa el plan Premium sin pasarela real (pago no disponible)."""
    usuario = _usuarioDeSesion(sesion)
    if usuario is None:
        flashForm(request, "No se encontro tu cuenta: inicia sesion "
                           "nuevamente.")
        return RedirectResponse("/users/login", status_code=303)
    user_model.setPlanUsuario(sesion.id_usuario, True)
    flashForm(request, "Pago simulado (demo) aceptado: plan Premium activado "
                       "para tu cuenta.", ok=True)
    return RedirectResponse("/users/perfil", status_code=303)


async def bajarPlan(request: Request,
                    id_sesion: UUID = Depends(session_cookie),
                    sesion: SessionData = Depends(verificador)):
    """Vuelve al plan Gratuito (para demostrar ambos estados)."""
    usuario = _usuarioDeSesion(sesion)
    if usuario is None:
        flashForm(request, "No se encontro tu cuenta: inicia sesion "
                           "nuevamente.")
        return RedirectResponse("/users/login", status_code=303)
    user_model.setPlanUsuario(sesion.id_usuario, False)
    flashForm(request, "Tu cuenta volvio al plan Gratuito.", ok=True)
    return RedirectResponse("/users/perfil", status_code=303)
