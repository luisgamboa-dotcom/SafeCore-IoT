"""
    Rutas de auth (registro, login, logout). Prefijo /users.
    Delegan en controllers/authController.py.
    Orden: fijas primero; las genéricas de usuarios viven en usersRoutes.py.
"""

# routers/authRoutes.py
from fastapi import APIRouter

import controllers.authController as authController

auth_router = APIRouter(prefix="/users", tags=["users"])


auth_router.get("/register")(authController.showRegisterForm)
auth_router.post("/register")(authController.registerUser)

auth_router.get("/login")(authController.showLoginForm)
auth_router.post("/login")(authController.loginUser)

auth_router.post("/logout")(authController.logoutUser)
