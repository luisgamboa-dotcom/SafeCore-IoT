"""
    Controlador de usuarios (MVC: Controller).
    Solo recibe la petición, valida, llama al modelo (models/users.py)
    y responde con una vista (templates/users-login/) o un redirect.
    Aquí NO hay SQL: todo el acceso a datos vive en el modelo.
    Las rutas que apuntan a estas funciones viven en routers/routes.py.
"""

# controllers/usersController.py
import hashlib
import hmac
from uuid import UUID, uuid4

import mysql.connector
from fastapi import Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessions import (
    SessionData,
    backend as session_backend,
    cookie as session_cookie,
    verificador,
)

# El controlador usa el modelo, validaciones y mensajes flash.
from models import users as user_model
from utils import users as user_utils
from utils.flash import flash_form, pop_form_flash

# Lo que en js se hace con app.set('view engine', 'ejs'), en fastapi se hace con Jinja2Templates()
# la carpeta templates debe estar en la raiz del proyecto, al mismo nivel que main.py.
templates = Jinja2Templates(directory="templates")


# index — lista todos los usuarios (ruta protegida: exige sesión)
def index(request: Request, id_sesion: UUID = Depends(session_cookie), sesion: SessionData = Depends(verificador)):
    users = user_model.get_all_users()
    flash_msg, _, flash_ok = pop_form_flash(request)
    # Retorna la plantilla index.html, y le pasa como contexto la variable users, que contiene los registros de la tabla usuarios.
    return templates.TemplateResponse(request, "users-login/index.html", {"request": request,
    "users": users, "flash_msg": flash_msg, "flash_ok": flash_ok})


# register — muestra el formulario (GET)
def register(request: Request):
    flash_msg, old, _ = pop_form_flash(request)
    return templates.TemplateResponse(request, "users-login/register.html",
        {"request": request, "flash_msg": flash_msg, "old": old})


# store — guarda un usuario nuevo (INSERT ... VALUES (...))
def store(
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
    form_data = user_utils.normalizar_formulario({"nombre": nombre,
                 "apellido": apellido,
                 "email": email,
                 "telefono": telefono,
                 "id_organizacion": id_organizacion,
                 "password": password,
                 "confirmPassword": confirmPassword
                 })

    # Para repoblar tras un error (las claves nunca se guardan ni se reenvían)
    old = {k: v for k, v in form_data.items() if k not in ("password", "confirmPassword")}

    def volver_con_error(mensaje):
        # Flash global único + redirect al GET (patrón PRG: F5 ya no reenvía el POST)
        flash_form(request, mensaje, old)
        return RedirectResponse("/users/register", status_code=303)

    # Validar correo
    correo_limpio, error_email = user_utils.validar_email(form_data["email"])
    if error_email:
        return volver_con_error(error_email)
    form_data["email"] = correo_limpio

    # Validar teléfono
    telefono_normalizado, error_telefono = user_utils.validar_telefono_chileno(form_data["telefono"])
    if error_telefono:
        return volver_con_error(error_telefono)

    error_claves = user_utils.validar_passwords(form_data["password"], form_data["confirmPassword"])
    if error_claves:
        return volver_con_error(error_claves)

    form_data["password_hash"] = hashlib.sha256(form_data["password"].encode()).hexdigest()


    try:
        user_model.create_user(
            form_data["nombre"],
            form_data["apellido"],
            form_data["email"],
            telefono_normalizado,
            form_data["password_hash"],
            int(form_data["id_organizacion"]) if form_data["id_organizacion"] else None)

    except mysql.connector.Error as e:
        if e.errno == 1062:
            return volver_con_error("Ese correo ya está registrado")
        if e.errno == 1452:
            return volver_con_error("La organización elegida no existe")
        return volver_con_error(f"Error al guardar: {e.msg}")
    # commit se hace dentro del modelo; si no se hace commit, los cambios no se guardan.
    flash_form(request, "Cuenta creada. ¡Bienvenido!", ok=True)
    return RedirectResponse("/users", status_code=303)


# login — muestra el formulario (público)
def login_form(request: Request):
    flash_msg, old, _ = pop_form_flash(request)
    return templates.TemplateResponse(request, "users-login/login.html",
        {"request": request, "flash_msg": flash_msg, "old": old})


# login — verifica credenciales y crea la sesión (público)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    ):
    ctx_old = {"email": email}

    def volver_con_error(mensaje):
        flash_form(request, mensaje, ctx_old)
        return RedirectResponse("/users/login", status_code=303)

    correo_limpio, error_email = user_utils.validar_email(email.strip())
    if error_email:
        return volver_con_error(error_email)

    user = user_model.get_user_by_email(correo_limpio)
    esperado = user["password_hash"] if user else ""
    recibido = hashlib.sha256(password.encode()).hexdigest()
    # Mensaje genérico a propósito: no revelar si falló el correo o la clave
    if user is None or not hmac.compare_digest(esperado, recibido):
        return volver_con_error("Correo o contraseña incorrectos")

    session_id = uuid4()
    await session_backend.create(session_id, SessionData(id_usuario=user["id_usuario"]))
    respuesta = RedirectResponse("/users", status_code=303)
    session_cookie.attach_to_response(respuesta, session_id)
    return respuesta


# logout — destruye la sesión y borra la cookie (público)
async def logout(request: Request, session_id: UUID = Depends(session_cookie)):
    try:
        await session_backend.delete(session_id)
    except Exception:
        pass  # logout idempotente: si no había sesión, igual se redirige
    flash_form(request, "Sesión cerrada correctamente.", ok=True)
    respuesta = RedirectResponse("/users/login", status_code=303)
    session_cookie.delete_from_response(respuesta)
    return respuesta


# sesiones — página TEMPORAL de depuración: muestra sesiones activas + usuarios.
# BORRAR antes de la entrega (ruta, template y botón del login).
def ver_sesiones(request: Request,
                 id_sesion: UUID = Depends(session_cookie),
                 sesion: SessionData = Depends(verificador)
                 ):
    sesiones = []
    for row in user_model.get_sesiones_activas():
        sesiones.append({
            "id": row["id_sesion"][:8] + "…",
            "id_usuario": row["id_usuario"],
            "nombre": row["nombre"] or "(eliminado)",
            "email": row["email"] or "(eliminado)",
        })
    usuarios = user_model.get_all_users()
    return templates.TemplateResponse(request, "users-login/sesiones.html",
        {"request": request, "sesiones": sesiones, "usuarios": usuarios})


# show muestra un usuario por id (SELECT ... WHERE id_usuario = %s)
def show(request: Request,
         id_usuario: int,
         id_sesion: UUID = Depends(session_cookie),
         sesion: SessionData = Depends(verificador)
         ):
    user = user_model.get_user_by_id(id_usuario)
    if user is None:
        return templates.TemplateResponse(request, "users-login/index.html", {"request": request})

    flash_msg, _, flash_ok = pop_form_flash(request)
    return templates.TemplateResponse(request, "users-login/show.html",
        {"request": request, "user": user, "flash_msg": flash_msg, "flash_ok": flash_ok})

def edit_form(request: Request,
              id_usuario: int,
              id_sesion: UUID = Depends(session_cookie),
              sesion: SessionData = Depends(verificador)
              ):
    user = user_model.get_user_by_id(id_usuario)
    if user is None:
        return templates.TemplateResponse(request, "users-login/index.html", {"request": request})

    return templates.TemplateResponse(request, "users-login/edit.html", {"request": request, "user": user})

def edit(
    request: Request,
    id_usuario: int,
    id_sesion: UUID = Depends(session_cookie),
    sesion: SessionData = Depends(verificador),
    nombre: str = Form(...),
    apellido: str = Form(""),
    email: str = Form(...),
    telefono: str = Form(""),
    id_organizacion: str = Form("")
    ):

    form_data = {"nombre": nombre,
                 "apellido": apellido,
                 "email": email,
                 "telefono": telefono,
                 "id_organizacion": id_organizacion
                 }

    try:
        user_model.update_user(
            id_usuario,
            form_data["nombre"],
            form_data["apellido"],
            form_data["email"],
            form_data["telefono"],
            int(form_data["id_organizacion"]) if form_data["id_organizacion"] else None,
            id_usuario
        )
        flash_form(request, "Usuario actualizado correctamente.", ok=True)
        return RedirectResponse(f"/users/{id_usuario}", status_code=303)
    except mysql.connector.Error as e:
        return templates.TemplateResponse(request, "users-login/show.html", {"request": request, "user": form_data, "error": "Error al actualizar el usuario"})
