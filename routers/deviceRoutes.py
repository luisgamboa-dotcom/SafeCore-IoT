from fastapi import APIRouter

import controllers.devicesController as devicesController
import controllers.mantenimientosController as mantenimientosController

devices_router = APIRouter(tags=["devices"])


devices_router.get("/dashboard/devices/{id_device}")(devicesController.showDeviceDetail)


devices_router.get("/dashboard/devices/{id_device}/export.csv")(devicesController.exportDeviceCsv)


devices_router.post("/dashboard/devices/{id_device}/mantenimientos")(mantenimientosController.storeMantenimiento)
devices_router.post("/dashboard/mantenimientos/{id_mantenimiento}/ejecutar")(mantenimientosController.registrarEjecucion)


devices_router.get("/admin/devices")(devicesController.showDevicesPage)
devices_router.get("/admin/devices/create")(devicesController.showCreateDeviceForm)
devices_router.post("/admin/devices")(devicesController.storeDevice)
devices_router.get("/admin/devices/{id_device}/edit")(devicesController.showEditDeviceForm)
devices_router.post("/admin/devices/{id_device}/update")(devicesController.updateDeviceFromAdmin)
devices_router.post("/admin/devices/{id_device}/delete")(devicesController.deleteDeviceFromAdmin)

devices_router.post("/admin/devices/{id_device}/toggle-active")(devicesController.toggleDeviceActive)
