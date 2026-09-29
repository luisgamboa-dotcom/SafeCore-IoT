"""
    Rutas del sistema (único archivo de rutas).
    Cada ruta delega en una función de controllers/ ({seccion}Controller.py).
    Prefijos y tags iguales que antes: no cambia ninguna URL.
"""

# routers/routes.py
from fastapi import APIRouter

import controllers.lecturasController as lecturasController
import controllers.usersController as usersController

# Mismo prefijo/tags que tenían users.router y lecturas.router.
users_router = APIRouter(prefix="/users", tags=["users"])
datos_router = APIRouter(tags=["ingest", "datos"])


# --- usuarios (controllers/usersController.py) ---
users_router.get("/")(usersController.index)

users_router.get("/register")(usersController.register)
users_router.post("/register")(usersController.store)

users_router.get("/login")(usersController.login_form)
users_router.post("/login")(usersController.login)

users_router.post("/logout")(usersController.logout)

users_router.get("/sesiones")(usersController.ver_sesiones)

users_router.get("/{id_usuario}")(usersController.show)

users_router.get("/{id_usuario}/edit")(usersController.edit_form)
users_router.post("/{id_usuario}/edit")(usersController.edit)


# --- lecturas y datos (controllers/lecturasController.py) ---
datos_router.post("/api/ingest")(lecturasController.ingest)
datos_router.get("/api/ultimas")(lecturasController.ultimas)
datos_router.get("/datos")(lecturasController.datos)
