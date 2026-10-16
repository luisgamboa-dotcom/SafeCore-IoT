"""Rutas de administración (solo rol Administrador)."""
from fastapi import APIRouter

import controllers.adminController as adminController

admin_router = APIRouter(prefix="/admin", tags=["admin"])


admin_router.get("")(adminController.showAdminPanel)
admin_router.get("/organizations/create")(adminController.showCreateOrganizationForm)
admin_router.get("/organizations/{id_organizacion}/edit")(adminController.showEditOrganizationForm)
admin_router.post("/organizations/{id_organizacion}/edit")(adminController.updateOrganization)
admin_router.post("/organizations/{id_organizacion}/delete")(adminController.deleteOrganization)
admin_router.get("/organizations/{id_organizacion}")(adminController.showOrganizationDetail)
admin_router.post("/organizations/{id_organizacion}/add-user")(adminController.addUserToOrganization)
admin_router.post("/organizations/{id_organizacion}/remove-user")(adminController.removeUserFromOrganization)
admin_router.get("/instalaciones/create")(adminController.showCreateInstalacionForm)
admin_router.get("/instalaciones/{id_instalacion}/edit")(adminController.showEditInstalacionForm)
admin_router.post("/instalaciones/{id_instalacion}/edit")(adminController.updateInstalacion)
admin_router.post("/instalaciones/{id_instalacion}/delete")(adminController.deleteInstalacion)
admin_router.get("/instalaciones/{id_instalacion}/zonas/create")(adminController.showCreateZonaForm)
admin_router.post("/instalaciones/{id_instalacion}/zonas")(adminController.storeZona)
admin_router.post("/instalaciones/{id_instalacion}/zonas/{id_zona}/delete")(adminController.deleteZona)
admin_router.get("/instalaciones/{id_instalacion}/zonas/{id_zona}")(adminController.showZonaDetail)
admin_router.get("/instalaciones/{id_instalacion}")(adminController.showInstalacionDetail)
admin_router.get("/instalaciones")(adminController.showInstalacionesPage)
admin_router.post("/instalaciones")(adminController.storeInstalacion)
admin_router.get("/users")(adminController.showUsersPage)
admin_router.get("/users/{id_usuario}/edit")(adminController.showEditUserForm)
admin_router.post("/users/{id_usuario}/edit")(adminController.updateUserFromAdmin)

admin_router.get("/organizations")(adminController.showOrganizationsPage)
admin_router.post("/organizations")(adminController.storeOrganization)
