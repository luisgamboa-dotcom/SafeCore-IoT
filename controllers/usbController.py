"""
    Controlador USB (MVC: Controller).
    Página de testeo en vivo: muestra lo que llega por USB sin guardar
    nada en la base de datos. Las rutas viven en routers/usbRoutes.py.
"""

# controllers/usbController.py
from fastapi import Request, Form
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from models import usbModel as usb_model

templates = Jinja2Templates(directory="templates")


def showUsbTestPage(request: Request):
    # Página pública de testeo, igual que /datos.
    return templates.TemplateResponse(request, "monitor/index.html", {"request": request})


def getUsbPorts():
    return {"ok": True, "ports": usb_model.listUsbPorts()}


def openUsbConnection(port: str = Form(...), baud: int = Form(9600)):
    ok, error = usb_model.openUsbPort(port, baud)
    if not ok:
        return JSONResponse(status_code=409, content={"ok": False, "error": error})
    return {"ok": True, "port": port, "baud": int(baud)}


def closeUsbConnection():
    usb_model.closeUsbPort()
    return {"ok": True}


def getLiveUsbLines(limit: int = 50):
    estado = usb_model.getUsbStatus()
    return {"ok": True, "connected": estado["connected"], "port": estado["port"],
            "baud": estado["baud"], "error": estado["error"],
            "lines": usb_model.getLiveLines(limit)}
