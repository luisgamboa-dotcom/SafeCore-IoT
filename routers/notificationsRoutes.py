"""Rutas del centro de notificaciones."""
from fastapi import APIRouter

import controllers.notificationsController as notificationsController

notifications_router = APIRouter(tags=["notifications"])


notifications_router.get("/dashboard/notificaciones")(notificationsController.showNotificacionesPage)
notifications_router.post("/dashboard/notificaciones/{id_notificacion}/leer")(notificationsController.marcarLeidaNotificacion)
