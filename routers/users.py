"""
    Controlador de usuarios (MVC: Controller).
    Solo recibe la petición, valida, llama al modelo (models/users.py)
    y responde con una vista (templates/users-login/) o un redirect.
    Aquí NO hay SQL: todo el acceso a datos vive en el modelo.
"""

# routers/users.py
import hashlib
import hmac
from uuid import UUID, uuid4

import mysql.connector
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.sessions import (
    SessionData,
    backend as session_backend,
    cookie as session_cookie,
    verificador,
)

# El controlador usa el modelo y los esquemas de validación.
from models import users as user_model
from utils import users as user_utils

# Lo que en js se hace con express.Router(), en fastapi se hace con APIRouter()
router = APIRouter()

# Lo que en js se hace con app.set('view engine', 'ejs'), en fastapi se hace con Jinja2Templates()
# la carpeta templates debe estar en la raiz del proyecto, al mismo nivel que main.py.
templates = Jinja2Templates(directory="templates")


# index — lista todos los usuarios (ruta protegida: exige sesión)
@router.get("/")
def index(request: Request, id_sesion: UUID = Depends(session_cookie), sesion: SessionData = Depends(verificador)):
    users = user_model.get_all_users()
    # Retorna la plantilla index.html, y le pasa como contexto la variable users, que contiene los registros de la tabla usuarios.
    return templates.TemplateResponse(request, "users-login/index.html", {"request": request,
    "users": users})


# register — muestra el formulario (GET)
@router.get("/register")
def register(request: Request):
    return templates.TemplateResponse(request, "users-login/register.html", {"request": request})


# store — guarda un usuario nuevo (INSERT ... VALUES (...))
@router.post("/register")
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

    def form_error(field_errors):
        # Primer mensaje como resumen global + dict por campo para resaltar cada input
        resumen = next(iter(field_errors.values()))
        return templates.TemplateResponse(
            request, "users-login/register.html",
            {**form_data, "error": resumen, "errors": field_errors})

    # Validar correo
    correo_limpio, error_email = user_utils.validar_email(form_data["email"])

    if error_email:
        return form_error({"email": error_email})
    
    form_data["email"] = correo_limpio

    # Validar teléfono
    telefono_normalizado, error_telefono = user_utils.validar_telefono_chileno(form_data["telefono"])
    if error_telefono:
        return form_error({"telefono": error_telefono})

    error_claves = user_utils.validar_passwords(form_data["password"], form_data["confirmPassword"])
    if error_claves:
        return form_error({"confirmPassword": error_claves})

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
            return form_error({"email": "Ese correo ya está registrado"})
        if e.errno == 1452:
            return form_error({"id_organizacion": "La organización elegida no existe"})
        return form_error({"email": f"Error al guardar: {e.msg}"})
    # commit se hace dentro del modelo; si no se hace commit, los cambios no se guardan.
    return RedirectResponse("/users", status_code=303)


# login — muestra el formulario (público)
@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "users-login/login.html", {"request": request})


# login — verifica credenciales y crea la sesión (público)
@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    ):
    ctx = {"request": request, "email": email}

    correo_limpio, error_email = user_utils.validar_email(email.strip())
    if error_email:
        return templates.TemplateResponse(
            request, "users-login/login.html",
            {**ctx, "error": error_email, "errors": {"email": error_email}})

    user = user_model.get_user_by_email(correo_limpio)
    esperado = user["password_hash"] if user else ""
    recibido = hashlib.sha256(password.encode()).hexdigest()
    # Mensaje genérico a propósito: no revelar si falló el correo o la clave
    if user is None or not hmac.compare_digest(esperado, recibido):
        mensaje = "Correo o contraseña incorrectos"
        return templates.TemplateResponse(
            request, "users-login/login.html",
            {**ctx, "error": mensaje, "errors": {"email": mensaje, "password": mensaje}})

    session_id = uuid4()
    await session_backend.create(session_id, SessionData(id_usuario=user["id_usuario"]))
    respuesta = RedirectResponse("/users", status_code=303)
    session_cookie.attach_to_response(respuesta, session_id)
    return respuesta


# logout — destruye la sesión y borra la cookie (público)
@router.post("/logout")
async def logout(session_id: UUID = Depends(session_cookie)):
    try:
        await session_backend.delete(session_id)
    except Exception:
        pass  # logout idempotente: si no había sesión, igual se redirige
    respuesta = RedirectResponse("/users/login", status_code=303)
    session_cookie.delete_from_response(respuesta)
    return respuesta


# sesiones — página TEMPORAL de depuración: muestra sesiones activas + usuarios.
# BORRAR antes de la entrega (ruta, template y botón del login).
@router.get("/sesiones")
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
@router.get("/{id_usuario}")
def show(request: Request,
         id_usuario: int,
         id_sesion: UUID = Depends(session_cookie),
         sesion: SessionData = Depends(verificador)
         ):
    user = user_model.get_user_by_id(id_usuario)
    if user is None:
        return templates.TemplateResponse(request, "users-login/index.html", {"request": request})

    return templates.TemplateResponse(request, "users-login/show.html", {"request": request, "user": user})

@router.get("/{id_usuario}/edit")
def edit_form(request: Request,
              id_usuario: int,
              id_sesion: UUID = Depends(session_cookie),
              sesion: SessionData = Depends(verificador)
              ):
    user = user_model.get_user_by_id(id_usuario)
    if user is None:
        return templates.TemplateResponse(request, "users-login/index.html", {"request": request})

    return templates.TemplateResponse(request, "users-login/edit.html", {"request": request, "user": user})

@router.post("/{id_usuario}/edit")
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
        return RedirectResponse(f"/users/{id_usuario}", status_code=303)
    except mysql.connector.Error as e:
        return templates.TemplateResponse(request, "users-login/show.html", {"request": request, "user": form_data, "error": "Error al actualizar el usuario"})
    
    