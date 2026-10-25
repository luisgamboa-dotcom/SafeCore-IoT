"""Device routes: dashboard device detail."""
from fastapi import APIRouter

import controllers.devicesController as devicesController

devices_router = APIRouter(tags=["devices"])


devices_router.get("/dashboard/devices/{id_device}")(devicesController.showDeviceDetail)

# Panel admin
devices_router.get("/admin/devices")(devicesController.showDevicesPage)
devices_router.get("/admin/devices/create")(devicesController.showCreateDeviceForm)
devices_router.post("/admin/devices")(devicesController.storeDevice)
devices_router.get("/admin/devices/{id_device}/edit")(devicesController.showEditDeviceForm)
devices_router.post("/admin/devices/{id_device}/update")(devicesController.updateDeviceFromAdmin)
devices_router.post("/admin/devices/{id_device}/delete")(devicesController.deleteDeviceFromAdmin)
