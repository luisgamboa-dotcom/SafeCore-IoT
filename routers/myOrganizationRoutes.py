"""My organization routes (/mi-organizacion)."""
from fastapi import APIRouter

import controllers.myOrganizationController as myOrganizationController

my_org_router = APIRouter(prefix="/mi-organizacion", tags=["my-organization"])


my_org_router.get("")(myOrganizationController.showMyOrganization)
my_org_router.get("/editar")(myOrganizationController.showEditMyOrganization)
my_org_router.post("/update")(myOrganizationController.updateMyOrganization)
my_org_router.get("/installations/create")(myOrganizationController.showCreateInstallationForm)
my_org_router.post("/installations")(myOrganizationController.storeInstallation)
my_org_router.get("/installations/{id_installation}/editar")(myOrganizationController.showEditInstallationForm)
my_org_router.post("/installations/{id_installation}/update")(myOrganizationController.updateInstallation)
my_org_router.get("/installations/{id_installation}/zones/create")(myOrganizationController.showCreateZoneForm)
my_org_router.post("/installations/{id_installation}/zones")(myOrganizationController.storeZone)
my_org_router.get("/zones/{id_zone}/editar")(myOrganizationController.showEditZoneForm)
my_org_router.post("/zones/{id_zone}/update")(myOrganizationController.updateZone)
