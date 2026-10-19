"""Device detail page (dashboard side)."""
from uuid import UUID

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from config.sessionsConfig import SessionData, cookie as session_cookie, verificador
from models import devicesModel as dev_model
from utils.commonUtils import userSessionContext

templates = Jinja2Templates(directory="templates")


def showDeviceDetail(request: Request,
                     id_device: int,
                     id_sesion: UUID = Depends(session_cookie),
                     sesion: SessionData = Depends(verificador)):
    dev = dev_model.getDeviceDetail(id_device)
    if dev is None:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "datos/device.html",
        {"request": request, "dev": dev, **userSessionContext(sesion)})
