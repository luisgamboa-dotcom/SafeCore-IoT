"""
    En comparacion a js, en python no se necesita un archivo de rutas para cada controlador,
    ya que se puede crear un router para cada controlador y luego importarlo en el main.py.
    En pocas palabras, el MVC se condensa en un solo archivo de rutas, pero se puede separar 
    en varios routers para cada controlador.
"""

# routers/users.py
import hashlib

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

# Esta linea importa la funcion get_conn() del archivo db.py, 
# que se encarga de crear la conexion a la base de datos.
from db import get_conn

# Lo que en js se hace con express.Router(), en fastapi se hace con APIRouter()
router = APIRouter()

# Lo que en js se hace con app.set('view engine', 'ejs'), en fastapi se hace con Jinja2Templates()
# la carpeta templates debe estar en la raiz del proyecto, al mismo nivel que main.py.
templates = Jinja2Templates(directory="templates")

"""
# index — equivale a postController.index (SELECT * FROM posts)
@router.get("/")
def index(request: Request):
    # Esta linea crea la conexion a la base de datos, y la variable conn es un objeto de tipo Connection.
    conn = get_conn()
    # Esta linea crea un cursor, que es un objeto que permite ejecutar consultas SQL y obtener resultados.
    cur = conn.cursor(dictionary=True)
    # Execute es el "query" que se solia usar en js, y fetchall() es el equivalente a rows en js.
    cur.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = cur.fetchall()
    # Cierra el cursor y la conexion a la base de datos, para liberar recursos.
    # Si no se cierran, se pueden generar errores de conexion y saturar la base de datos.
    cur.close(); conn.close()
    # Retorna la plantilla index.html, y le pasa como contexto la variable posts, que contiene los registros de la tabla posts.
    return templates.TemplateResponse(request, "post/index.html", {"request": request,
    "posts": posts})
"""

# create — equivale a postController.create (solo muestra formulario)
@router.get("/")
def create(request: Request):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios ORDER BY id_usuario DESC")
    users = cur.fetchall()
    cur.close(); conn.close()
    return templates.TemplateResponse(request, "users-login/index.html", {"request": request,
    "users": users})


# register — muestra el formulario (GET)
@router.get("/register")
def register(request: Request):
    return templates.TemplateResponse(request, "users-login/register.html", {"request": request})


# store — equivale a postController.store (INSERT ... VALUES (?,?))
@router.post("/register")
def store(
    request: Request,
    nombre: str = Form(...),
    apellido: str = Form(""),
    email: str = Form(...),
    telefono: str = Form(""),
    password: str = Form(...),
    confirmPassword: str = Form(...),
    id_organizacion: str = Form(""),
    terms: bool = Form(...),
    ):
    if password != confirmPassword:
        return templates.TemplateResponse(request, "users-login/register.html", {"request": request, "error": "Passwords do not match"})
    conn = get_conn()
    cur = conn.cursor()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    cur.execute("INSERT INTO usuarios (nombre, apellido, email, telefono, password_hash, id_organizacion) VALUES (%s, %s, %s, %s, %s, %s)",
                (nombre, apellido, email, telefono or None, password_hash, int(id_organizacion) if id_organizacion else None))
    # commit es necesario para que los cambios se guarden en la base de datos, si no se hace commit, los cambios no se guardan.
    # Es lo que vimos en la clase con el profesor Francisco Pareja, donde usabamos BEGIN y COMMIT para guardar los cambios en la base de datos.
    conn.commit()
    cur.close(); conn.close()
    return RedirectResponse("/users", status_code=303)
