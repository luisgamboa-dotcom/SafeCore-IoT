import hashlib
import hmac
import os
from uuid import UUID, uuid4

import mysql.connector
from fastapi import Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessionsConfig import (
    SessionData,
    backend as session_backend,
    cookie as session_cookie,
    verificador,
)

from models import usersModel as user_model
from models import passwordResetModel as password_model
from utils import authUtils as user_utils
from utils import emailUtils as email_utils
from utils.flashUtils import flashForm, popFormFlash

templates = Jinja2Templates(directory="templates")

def showRegisterForm(request: Request):
    flash_msg, old, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "users-login/register.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok, "old": old})

def registerUser(
    request: Request,
    nombre: str = Form(...),
    apellido: str = Form(""),
    email: str = Form(...),
    telefono: str = Form(""),
    password: str = Form(...),
    confirmPassword: str = Form(...)
    ):

    form_data = user_utils.normalizeForm({"nombre": nombre,
                 "apellido": apellido,
                 "email": email,
                 "telefono": telefono,
                 "password": password,
                 "confirmPassword": confirmPassword
                 })
    old = {k: v for k, v in form_data.items() if k not in ("password", "confirmPassword")}

    def redirectWithError(mensaje):
        flashForm(request, mensaje, old)
        return RedirectResponse("/users/register", status_code=303)

    correo_limpio, error_email = user_utils.validateEmail(form_data["email"])
    if error_email:
        return redirectWithError(error_email)
    form_data["email"] = correo_limpio

    telefono_normalizado, error_telefono = user_utils.validateChileanPhone(form_data["telefono"])
    if error_telefono:
        return redirectWithError(error_telefono)

    error_claves = user_utils.validatePasswords(form_data["password"], form_data["confirmPassword"])
    if error_claves:
        return redirectWithError(error_claves)

    form_data["password_hash"] = hashlib.sha256(form_data["password"].encode()).hexdigest()


    try:
        nuevo_id = user_model.createUser(
            form_data["nombre"],
            form_data["apellido"],
            form_data["email"],
            telefono_normalizado,
            form_data["password_hash"],
            None)
        id_rol_usuario = user_model.getRoleIdByName("Usuario")
        if id_rol_usuario is not None:
            user_model.assignRole(nuevo_id, id_rol_usuario)

    except mysql.connector.Error as e:
        if e.errno == 1062:
            return redirectWithError("Ese correo ya está registrado")
        return redirectWithError(f"Error al guardar: {e.msg}")
    flashForm(request, "Cuenta creada. ¡Bienvenido!", ok=True)
    return RedirectResponse("/dashboard", status_code=303)

def showLoginForm(request: Request):
    flash_msg, old, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "users-login/login.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok, "old": old})

async def loginUser(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    ):

    ctx_old = {"email": email}

    def redirectWithError(mensaje):
        flashForm(request, mensaje, ctx_old)
        return RedirectResponse("/users/login", status_code=303)

    correo_limpio, error_email = user_utils.validateEmail(email.strip())
    if error_email:
        return redirectWithError(error_email)

    user = user_model.getUserByEmail(correo_limpio)
    esperado = user["password_hash"] if user else ""
    recibido = hashlib.sha256(password.encode()).hexdigest()
    if user is None or not hmac.compare_digest(esperado, recibido):
        return redirectWithError("Correo o contraseña incorrectos")
    
    if user["id_usuario_estado"] != 1:
        return redirectWithError("Cuenta inactiva. Contacte al administrador.")

    session_id = uuid4()
    await session_backend.create(session_id, SessionData(id_usuario=user["id_usuario"]))
    flashForm(request, "Sesión iniciada correctamente. ¡Bienvenido!", ok=True)
    respuesta = RedirectResponse("/dashboard", status_code=303)
    session_cookie.attach_to_response(respuesta, session_id)
    return respuesta

def redirectToDashboard(request: Request, id_sesion: UUID = Depends(session_cookie), sesion: SessionData = Depends(verificador)):
    return RedirectResponse("/dashboard", status_code=303)

async def logoutUser(request: Request, session_id: UUID = Depends(session_cookie)):
    try:
        await session_backend.delete(session_id)
    except Exception:
        pass
    flashForm(request, "Sesión cerrada correctamente.", ok=True)
    respuesta = RedirectResponse("/users/login", status_code=303)
    session_cookie.delete_from_response(respuesta)
    return respuesta




def showRecuperarForm(request: Request):
    flash_msg, old, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "users-login/recuperar.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok, "old": old})


def requestPasswordReset(request: Request, email: str = Form(...)):
    ctx_old = {"email": email}

    def redirectWithMsg(mensaje, ok=False):
        flashForm(request, mensaje, ctx_old, ok=ok)
        return RedirectResponse("/users/recuperar", status_code=303)

    correo_limpio, error_email = user_utils.validateEmail(email.strip())
    if error_email:
        return redirectWithMsg(error_email)

    user = user_model.getUserByEmail(correo_limpio)
    if user is None or user["id_usuario_estado"] != 1:
        return redirectWithMsg(
            "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña.",
            ok=True)

    enlace = (os.getenv("APP_BASE_URL") or "http://localhost:8000") \
        + "/users/restablecer/" + password_model.createToken(user["id_usuario"])
    try:
        email_utils.sendPasswordResetEmail(correo_limpio, user["nombre"], enlace)
    except Exception:
        return redirectWithMsg("No se pudo enviar el correo de recuperación. Inténtalo más tarde.")
    return redirectWithMsg(
        "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña.",
        ok=True)


def showRestablecerForm(request: Request, token: str):
    fila = password_model.getValidToken(token)
    if fila is None:
        return redirRecuperarConError(request)
    flash_msg, old, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "users-login/restablecer.html",
        {"request": request, "token": token, "flash_msg": flash_msg,
         "flash_ok": flash_ok, "old": old})


def resetPassword(
    request: Request,
    token: str,
    password: str = Form(...),
    confirmPassword: str = Form(...)
    ):
    fila = password_model.getValidToken(token)
    if fila is None:
        return redirRecuperarConError(request)

    error_claves = user_utils.validatePasswords(password, confirmPassword)
    if error_claves:
        flashForm(request, error_claves)
        return RedirectResponse(f"/users/restablecer/{token}", status_code=303)

    user_model.updatePasswordHash(fila["id_usuario"],
                                  hashlib.sha256(password.encode()).hexdigest())
    password_model.markUsed(fila["id_token"])
    flashForm(request, "Contraseña restablecida correctamente. Inicia sesión con tu nueva clave.", ok=True)
    return RedirectResponse("/users/login", status_code=303)


def redirRecuperarConError(request: Request):
    flashForm(request, "El enlace es inválido o ya expiró. Solicita uno nuevo.")
    return RedirectResponse("/users/recuperar", status_code=303)
