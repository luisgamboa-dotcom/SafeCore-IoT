"""
    Controlador de auth (MVC: Controller).
    Solo autenticación: mostrar/procesar registro, login y logout.
    Las consultas viven en models/usersModel.py y las validaciones
    en utils/authUtils.py. Las rutas viven en routers/authRoutes.py.
"""

# controllers/authController.py
import hashlib
import hmac
from uuid import UUID, uuid4

import mysql.connector
from fastapi import Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessionsConfig import (
    SessionData,
    backend as session_backend,
    cookie as session_cookie,
)

# El controlador usa el modelo, validaciones y mensajes flash.
from models import usersModel as user_model
from utils import authUtils as user_utils
from utils.flashUtils import flashForm, popFormFlash

# Lo que en js se hace con app.set('view engine', 'ejs'), en fastapi se hace con Jinja2Templates()
# la carpeta templates debe estar en la raiz del proyecto, al mismo nivel que main.py.
templates = Jinja2Templates(directory="templates")


# register — muestra el formulario (GET)
def showRegisterForm(request: Request):
    flash_msg, old, _ = popFormFlash(request)
    return templates.TemplateResponse(request, "users-login/register.html",
        {"request": request, "flash_msg": flash_msg, "old": old})


# store — guarda un usuario nuevo (INSERT ... VALUES (...))
def registerUser(
    request: Request,
    nombre: str = Form(...),
    apellido: str = Form(""),
    email: str = Form(...),
    telefono: str = Form(""),
    password: str = Form(...),
    confirmPassword: str = Form(...),
    id_organizacion: str = Form("")
    ):

    # Datos para repoblar el formulario si hay error.
    # Normalización (strip + capitalize) y validación viven en utils;
    # el controlador solo orquesta e invoca funciones exportadas.
    form_data = user_utils.normalizeForm({"nombre": nombre,
                 "apellido": apellido,
                 "email": email,
                 "telefono": telefono,
                 "id_organizacion": id_organizacion,
                 "password": password,
                 "confirmPassword": confirmPassword
                 })

    # Para repoblar tras un error (las claves nunca se guardan ni se reenvían)
    old = {k: v for k, v in form_data.items() if k not in ("password", "confirmPassword")}

    def redirectWithError(mensaje):
        # Flash global único + redirect al GET (patrón PRG: F5 ya no reenvía el POST)
        flashForm(request, mensaje, old)
        return RedirectResponse("/users/register", status_code=303)

    # Validar correo
    correo_limpio, error_email = user_utils.validateEmail(form_data["email"])
    if error_email:
        return redirectWithError(error_email)
    form_data["email"] = correo_limpio

    # Validar teléfono
    telefono_normalizado, error_telefono = user_utils.validateChileanPhone(form_data["telefono"])
    if error_telefono:
        return redirectWithError(error_telefono)

    error_claves = user_utils.validatePasswords(form_data["password"], form_data["confirmPassword"])
    if error_claves:
        return redirectWithError(error_claves)

    form_data["password_hash"] = hashlib.sha256(form_data["password"].encode()).hexdigest()


    try:
        user_model.createUser(
            form_data["nombre"],
            form_data["apellido"],
            form_data["email"],
            telefono_normalizado,
            form_data["password_hash"],
            int(form_data["id_organizacion"]) if form_data["id_organizacion"] else None)

    except mysql.connector.Error as e:
        if e.errno == 1062:
            return redirectWithError("Ese correo ya está registrado")
        if e.errno == 1452:
            return redirectWithError("La organización elegida no existe")
        return redirectWithError(f"Error al guardar: {e.msg}")
    # commit se hace dentro del modelo; si no se hace commit, los cambios no se guardan.
    flashForm(request, "Cuenta creada. ¡Bienvenido!", ok=True)
    return RedirectResponse("/users", status_code=303)


# login — muestra el formulario (público)
def showLoginForm(request: Request):
    flash_msg, old, _ = popFormFlash(request)
    return templates.TemplateResponse(request, "users-login/login.html",
        {"request": request, "flash_msg": flash_msg, "old": old})


# login — verifica credenciales y crea la sesión (público)
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
    # Mensaje genérico a propósito: no revelar si falló el correo o la clave
    if user is None or not hmac.compare_digest(esperado, recibido):
        return redirectWithError("Correo o contraseña incorrectos")
    
    if user["id_usuario_estado"] != 1:
        return redirectWithError("Cuenta inactiva. Contacte al administrador.")

    session_id = uuid4()
    await session_backend.create(session_id, SessionData(id_usuario=user["id_usuario"]))
    respuesta = RedirectResponse("/users", status_code=303)
    session_cookie.attach_to_response(respuesta, session_id)
    return respuesta


# logout destruye la sesión y borra la cookie (público)
async def logoutUser(request: Request, session_id: UUID = Depends(session_cookie)):
    try:
        await session_backend.delete(session_id)
    except Exception:
        pass  # si no había sesión, igual se redirige
    flashForm(request, "Sesión cerrada correctamente.", ok=True)
    respuesta = RedirectResponse("/users/login", status_code=303)
    session_cookie.delete_from_response(respuesta)
    return respuesta
