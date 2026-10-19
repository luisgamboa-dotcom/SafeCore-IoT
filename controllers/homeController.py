"""Landing page and home redirects."""
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
    ctx = userSessionContext(sesion) if sesion is not None else {"logged": None, "iniciales": None}
    return templates.TemplateResponse(request, "landing.html",
        {"request": request, **ctx})
