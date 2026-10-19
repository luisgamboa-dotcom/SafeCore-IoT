"""Auth routes: register, login, logout (/users)."""
from fastapi import APIRouter

import controllers.authController as authController

auth_router = APIRouter(prefix="/users", tags=["users"])


auth_router.get("/")(authController.redirectToDashboard)

auth_router.get("/register")(authController.showRegisterForm)
auth_router.post("/register")(authController.registerUser)

auth_router.get("/login")(authController.showLoginForm)
auth_router.post("/login")(authController.loginUser)

auth_router.post("/logout")(authController.logoutUser)
