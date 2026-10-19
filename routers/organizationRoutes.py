"""Admin organizations routes (/admin/organizations)."""
from fastapi import APIRouter

import controllers.organizationsController as organizationsController

admin_router = APIRouter(prefix="/admin", tags=["admin"])


admin_router.get("/organizations")(organizationsController.showOrganizationsPage)
admin_router.post("/organizations")(organizationsController.storeOrganization)
admin_router.get("/organizations/create")(organizationsController.showCreateOrganizationForm)
admin_router.get("/organizations/{id_organization}/edit")(organizationsController.showEditOrganizationForm)
admin_router.post("/organizations/{id_organization}/edit")(organizationsController.updateOrganization)
admin_router.post("/organizations/{id_organization}/delete")(organizationsController.deleteOrganization)
admin_router.get("/organizations/{id_organization}")(organizationsController.showOrganizationDetail)
admin_router.post("/organizations/{id_organization}/add-user")(organizationsController.addUserToOrganization)
admin_router.post("/organizations/{id_organization}/remove-user")(organizationsController.removeUserFromOrganization)
