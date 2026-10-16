"""Controlador de usuarios: /users redirige al dashboard."""
from uuid import UUID

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse

from config.sessionsConfig import (
    SessionData,
    cookie as session_cookie,
    verificador,
)


# /users — redirige al dashboard (el listado de prueba fue eliminado)
def redirectToDashboard(request: Request, id_sesion: UUID = Depends(session_cookie), sesion: SessionData = Depends(verificador)):
    return RedirectResponse("/dashboard", status_code=303)