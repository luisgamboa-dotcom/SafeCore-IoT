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

# Recuperacion de contrasena (HU-003)
auth_router.get("/recuperar")(authController.showRecuperarForm)
auth_router.post("/recuperar")(authController.requestPasswordReset)
auth_router.get("/restablecer/{token}")(authController.showRestablecerForm)
auth_router.post("/restablecer/{token}")(authController.resetPassword)

# Perfil del usuario conectado (circulo de iniciales del panel).
auth_router.get("/perfil")(profileController.showMyProfile)
auth_router.post("/perfil")(profileController.updateMyProfile)
