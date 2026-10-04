"""
    Rutas de usuarios (listado, detalle, edición). Prefijo /users.
    Delegan en controllers/usersController.py.
    Orden: fija (/) primero, genéricas (/{id_usuario}) al final.
"""

# routers/usersRoutes.py
from fastapi import APIRouter

import controllers.usersController as usersController

users_router = APIRouter(prefix="/users", tags=["users"])


users_router.get("/")(usersController.listUsers)

users_router.get("/{id_usuario}/edit")(usersController.showEditUserForm)
users_router.post("/{id_usuario}/edit")(usersController.updateUser)

users_router.get("/{id_usuario}")(usersController.showUser)
