"""Rutas de autenticación: registro, inicio y cierre de sesión (/users)."""
from fastapi import APIRouter

import controllers.authController as authController
import controllers.profileController as profileController

auth_router = APIRouter(prefix="/users", tags=["users"])


auth_router.get("/")(authController.redirectToDashboard)

auth_router.get("/register")(authController.showRegisterForm)
auth_router.post("/register")(authController.registerUser)

auth_router.get("/login")(authController.showLoginForm)
auth_router.post("/login")(authController.loginUser)

auth_router.post("/logout")(authController.logoutUser)

# Perfil del usuario conectado (circulo de iniciales del panel).
auth_router.get("/perfil")(profileController.showMyProfile)
auth_router.post("/perfil")(profileController.updateMyProfile)
