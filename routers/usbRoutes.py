"""
    Rutas USB de testeo en vivo (sin guardar en la base de datos).
    Delegan en controllers/usbController.py.
"""

# routers/usbRoutes.py
from fastapi import APIRouter

import controllers.usbController as usbController

usb_router = APIRouter(tags=["usb"])


usb_router.get("/monitor")(usbController.showUsbTestPage)
usb_router.get("/api/usb/ports")(usbController.getUsbPorts)
usb_router.post("/api/usb/open")(usbController.openUsbConnection)
usb_router.post("/api/usb/close")(usbController.closeUsbConnection)
usb_router.get("/api/usb/live")(usbController.getLiveUsbLines)
