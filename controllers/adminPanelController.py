"""Admin panel home page."""
from uuid import UUID

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates
from config.sessionsConfig import SessionData, cookie as session_cookie, requireAdminUser
from models import usersModel as user_model
from utils.commonUtils import adminContext
from utils.flashUtils import popFormFlash

templates = Jinja2Templates(directory="templates")


def showAdminPanel(request: Request,
                   id_sesion: UUID = Depends(session_cookie),
                   sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/index.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})
