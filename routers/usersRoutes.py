"""Rutas de usuarios: /users redirige al dashboard."""
from fastapi import APIRouter

import controllers.usersController as usersController

users_router = APIRouter(prefix="/users", tags=["users"])


users_router.get("/")(usersController.redirectToDashboard)