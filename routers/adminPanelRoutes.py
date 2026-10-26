"""Rutas de inicio del panel admin (/admin)."""
from fastapi import APIRouter

import controllers.adminPanelController as adminPanelController

admin_router = APIRouter(prefix="/admin", tags=["admin"])


admin_router.get("")(adminPanelController.showAdminPanel)
