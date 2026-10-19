# Sesion firmada con cookies y backend MySQL
import os
from uuid import UUID

from dotenv import load_dotenv

from fastapi import Depends, HTTPException, Request

from fastapi_sessions.backends.session_backend import (
    BackendError,
    SessionBackend
)

from fastapi_sessions.frontends.session_frontend import FrontendError
from fastapi_sessions.frontends.implementations import (
    CookieParameters,
    SessionCookie,
)

from fastapi_sessions.session_verifier import SessionVerifier

from pydantic import BaseModel

from models import sessionsModel as sessionModel

load_dotenv()


class SessionData(BaseModel):
    id_usuario: int


cookie_params = CookieParameters(max_age=8 * 60 * 60)

cookie = SessionCookie(
    cookie_name="safecore_session",
    identifier="safecore_verifier",
    # auto_error=False: El verificador responde con un 303 -> /users/login (Verdadero responderia con un error de JSON)
    auto_error=False,
    secret_key=os.getenv("SECRET_KEY"),
    cookie_params=cookie_params,
)

class MySQLBackend(SessionBackend[UUID, SessionData]):
    async def create(self, session_id: UUID, data: SessionData):
        if sessionModel.sessionExists(str(session_id)):
            raise BackendError("create can't overwrite an existing session")
        sessionModel.createSession(str(session_id), data.id_usuario)

    async def read(self, session_id: UUID):
        try:
            id_usuario = sessionModel.getSessionUserId(str(session_id))
        except Exception as e:
            raise BackendError(f"read error: {e}")
        if id_usuario is None:
            return None
        return SessionData(id_usuario=id_usuario)

    async def update(self, session_id: UUID, data: SessionData) -> None:
        if sessionModel.updateSessionUser(str(session_id), data.id_usuario) == 0:
            raise BackendError("session does not exist, cannot update")

    async def delete(self, session_id: UUID) -> None:
        sessionModel.deleteSession(str(session_id))

backend: MySQLBackend = MySQLBackend()


class VerificadorSesion(SessionVerifier[UUID, SessionData]):
    def __init__(self):
        self._identifier = cookie.identifier
        self._auto_error = True
        self._backend = backend
        self._auth_http_exception = HTTPException(
            status_code=303, headers={"Location": "/users/login"}
        )

    @property
    def identifier(self):
        return self._identifier

    @property
    def auto_error(self):
        return self._auto_error

    @property
    def backend(self):
        return self._backend

    @property
    def auth_http_exception(self):
        return self._auth_http_exception

    def verify_session(self, model: SessionData) -> bool:
        return model.id_usuario > 0


verificador = VerificadorSesion()


async def getOptionalSession(request: Request):
    try:
        session_id = cookie(request)
    except Exception:
        return None
    if isinstance(session_id, FrontendError):
        return None
    try:
        return await backend.read(session_id)
    except Exception:
        return None


async def requireAdminUser(request: Request,
                           id_sesion: UUID = Depends(cookie),
                           sesion: SessionData = Depends(verificador)):
    # Role is checked on every request so revocation is immediate.
    from models import usersModel as user_model
    from utils.flashUtils import flashForm
    if "Administrador" not in user_model.getUserRoles(sesion.id_usuario):
        flashForm(request, "Acceso denegado: tu usuario no tiene permisos de administrador.")
        raise HTTPException(status_code=303, headers={"Location": "/users/login"})
    return sesion