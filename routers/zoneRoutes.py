"""Admin zones routes (/admin/installations/{id}/zones...)."""
from fastapi import APIRouter

import controllers.zonesController as zonesController

admin_router = APIRouter(prefix="/admin", tags=["admin"])


admin_router.get("/installations/{id_installation}/zones/create")(zonesController.showCreateZoneForm)
admin_router.post("/installations/{id_installation}/zones")(zonesController.storeZone)
admin_router.post("/installations/{id_installation}/zones/{id_zone}/delete")(zonesController.deleteZone)
admin_router.get("/installations/{id_installation}/zones/{id_zone}")(zonesController.showZoneDetail)
