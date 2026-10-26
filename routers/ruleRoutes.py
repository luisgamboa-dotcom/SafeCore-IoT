"""Rutas de reglas de alerta: POST solo de administración, anidados bajo la ficha del dispositivo."""
from fastapi import APIRouter

import controllers.rulesController as rulesController

rules_router = APIRouter(tags=["rules"])


rules_router.post("/admin/devices/{id_device}/rules")(rulesController.storeRule)
rules_router.post("/admin/devices/{id_device}/rules/{id_regla}/update")(rulesController.updateRule)
rules_router.post("/admin/devices/{id_device}/rules/{id_regla}/delete")(rulesController.deleteRule)
