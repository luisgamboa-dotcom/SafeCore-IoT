from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from config.sessionsConfig import getOptionalSession
from utils.commonUtils import userSessionContext

templates = Jinja2Templates(directory="templates")


def redirectToHome():
    return RedirectResponse("/home", status_code=303)


async def showHome(request: Request):
    sesion = await getOptionalSession(request)
    if sesion is not None:
        from models import usersModel as user_model
        from utils.flashUtils import popFormFlash
        usuario = user_model.getUserById(sesion.id_usuario)
        flash_msg, old, flash_ok = popFormFlash(request)
        ctx = {**userSessionContext(sesion),
               "sesion_activa": True,
               "usuario_email": usuario["email"] if usuario else None,
               "flash_msg": flash_msg, "flash_ok": flash_ok, "old": old}
    else:
        ctx = {"logged": None, "iniciales": None, "sesion_activa": False,
               "usuario_email": None,
               "flash_msg": None, "flash_ok": False, "old": {}}
    return templates.TemplateResponse(request, "landing.html",
        {"request": request, **ctx})
