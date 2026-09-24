"""
    Controlador de usuarios (MVC: Controller).
    Solo recibe la petición, valida, llama al modelo (models/users.py)
    y responde con una vista (templates/users-login/) o un redirect.
    Aquí NO hay SQL: todo el acceso a datos vive en el modelo.
"""

# routers/users.py
import hashlib

import mysql.connector
import phonenumbers
from email_validator import validate_email, EmailNotValidError
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from phonenumbers import NumberParseException

# El controlador usa el modelo, igual que en Express el controller usa el model.
from models import users as user_model

# Lo que en js se hace con express.Router(), en fastapi se hace con APIRouter()
router = APIRouter()

# Lo que en js se hace con app.set('view engine', 'ejs'), en fastapi se hace con Jinja2Templates()
# la carpeta templates debe estar en la raiz del proyecto, al mismo nivel que main.py.
templates = Jinja2Templates(directory="templates")


def validar_telefono_chileno(telefono_raw, pais_defecto="CL"):
    """Valida un teléfono con formato chileno por defecto.

    Acepta "912345678", "+56912345678", con espacios/guiones/paréntesis.
    Retorna (digitos_solo_numeros, None) si es válido, (None, mensaje) si no.
    Vacío -> (None, None) porque el campo es opcional.
    """
    if not telefono_raw or not telefono_raw.strip():
        return None, None
    try:
        numero_parseado = phonenumbers.parse(telefono_raw.strip(), pais_defecto)
        # is_possible_number: largo y prefijo plausibles para Chile (9 dígitos móvil, etc.).
        # No se usa is_valid_number porque su metadata rechaza rangos de prueba como 912345678.
        if not phonenumbers.is_possible_number(numero_parseado):
            return None, "El número de teléfono no es válido para Chile."
        telefono_solo_digitos = phonenumbers.format_number(
            numero_parseado,
            phonenumbers.PhoneNumberFormat.E164
        ).lstrip("+")
        return telefono_solo_digitos, None
    except NumberParseException:
        return None, "El número de teléfono no es válido."


# index — lista todos los usuarios (SELECT * FROM usuarios)
@router.get("/")
def index(request: Request):
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

    # Datos para repoblar el formulario si hay error
    form_data = {"nombre": nombre,
                 "apellido": apellido,
                 "email": email,
                 "telefono": telefono,
                 "id_organizacion": id_organizacion,
                 "password": password,
                 "confirmPassword": confirmPassword
                 }

    for key, value in form_data.items():
        form_data[key] = value.strip()

    form_data["nombre"] = form_data["nombre"].capitalize()
    form_data["apellido"] = form_data["apellido"].capitalize()

    def form_error(field_errors):
        # Primer mensaje como resumen global + dict por campo para resaltar cada input
        resumen = next(iter(field_errors.values()))
        return templates.TemplateResponse(
            request, "users-login/register.html",
            {**form_data, "error": resumen, "errors": field_errors})

    try:
        # validate_email comprueba la sintaxis; sin deliverability para no depender del DNS
        email_info = validate_email(form_data["email"], check_deliverability=False)
        # Siempre usa la versión normalizada para guardar en la Base de Datos (ej. pasa a minúsculas)
        form_data["email"] = email_info.normalized

    except EmailNotValidError:
        # Si falla, el correo está mal escrito o tiene sintaxis inválida
        return form_error({"email": "El correo electrónico no es válido. Revísalo e inténtalo de nuevo."})

    telefono_normalizado, error_telefono = validar_telefono_chileno(form_data["telefono"])
    if error_telefono:
        return form_error({"telefono": error_telefono})

    if form_data["password"] != form_data["confirmPassword"]:
        return form_error({"confirmPassword": "Las contraseñas no coinciden"})

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


# show — muestra un usuario por id (SELECT ... WHERE id_usuario = %s)
@router.get("/{id_usuario}")
def show(request: Request,
         id_usuario: int
         ):
    user = user_model.get_user_by_id(id_usuario)
    if user is None:
        return templates.TemplateResponse(request, "users-login/index.html", {"request": request})

    return templates.TemplateResponse(request, "users-login/show.html", {"request": request, "user": user})
