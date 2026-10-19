"""Device routes: dashboard device detail."""
from fastapi import APIRouter

import controllers.devicesController as devicesController

devices_router = APIRouter(tags=["devices"])


devices_router.get("/dashboard/devices/{id_device}")(devicesController.showDeviceDetail)
