"""Rutas de inicio: página de bienvenida y redirección raíz."""
from fastapi import APIRouter

import controllers.homeController as homeController

home_router = APIRouter(tags=["home"])


home_router.get("/", include_in_schema=False)(homeController.redirectToHome)
home_router.get("/home")(homeController.showHome)
