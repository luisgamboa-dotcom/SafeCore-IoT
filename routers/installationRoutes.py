"""Admin installations routes (/admin/installations)."""
from fastapi import APIRouter

import controllers.installationsController as installationsController

admin_router = APIRouter(prefix="/admin", tags=["admin"])


admin_router.get("/installations")(installationsController.showInstallationsPage)
admin_router.post("/installations")(installationsController.storeInstallation)
admin_router.get("/installations/create")(installationsController.showCreateInstallationForm)
admin_router.get("/installations/{id_installation}/edit")(installationsController.showEditInstallationForm)
admin_router.post("/installations/{id_installation}/edit")(installationsController.updateInstallation)
admin_router.post("/installations/{id_installation}/delete")(installationsController.deleteInstallation)
admin_router.get("/installations/{id_installation}")(installationsController.showInstallationDetail)
