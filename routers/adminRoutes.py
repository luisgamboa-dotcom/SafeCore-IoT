"""Rutas de administración (solo rol Administrador)."""
from fastapi import APIRouter

import controllers.adminController as adminController

admin_router = APIRouter(prefix="/admin", tags=["admin"])


admin_router.get("/users")(adminController.showUsersPage)
admin_router.get("/users/{id_usuario}/edit")(adminController.showEditUserForm)
admin_router.post("/users/{id_usuario}/edit")(adminController.updateUserFromAdmin)
