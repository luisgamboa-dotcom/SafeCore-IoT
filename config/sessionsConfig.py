# config/sessionsConfig.py — sesiones con fastapi-sessions (cookie firmada).
import os
# UUID es el identificador de sesión que viaja en la cookie firmada.
from uuid import UUID

from dotenv import load_dotenv

# Importamos HTTPException para poder devolver un error 303 (redirección) cuando la sesión no es válida.
from fastapi import HTTPException

# Importamos fastapi_sessions para manejar sesiones con cookies firmadas.
# BackendError es la excepción que lanza el backend cuando hay un error de almacenamiento.
# SessionBackend es la clase base para crear un backend de almacenamiento de sesiones.
from fastapi_sessions.backends.session_backend import (
    BackendError, 
    SessionBackend
)

# Importamos fastapi_sessions.frontends.implementations para manejar cookies firmadas.
# CookeiParameters es la clase que define los parámetros de la cookie (nombre, duración, etc)
# SessionCookie es la clase que implementa la cookie firmada.
from fastapi_sessions.frontends.implementations import (
    CookieParameters,
    SessionCookie,
)

# Importamos fastapi_sessions.session_verifier para verificar la validez de la sesión.
# SessionVerifier es la clase base para crear un verificador de sesiones.
from fastapi_sessions.session_verifier import SessionVerifier

# Importamos pydantic para definir el modelo de datos de la sesión.
# BaseModel es la clase base para crear modelos de datos con validación y serialización.
from pydantic import BaseModel

from models import sessionsModel as sessionModel

load_dotenv()


class SessionData(BaseModel):
    # Lo único que viaja en la cookie es el id del usuario logueado
    id_usuario: int


# Cookie de 8 horas (tambien es anti-XSS).
# XSS es un ataque que inyecta código malicioso en la página web, y la cookie firmada evita que el atacante pueda modificarla.

cookie_params = CookieParameters(max_age= 8 * 60 * 60)

cookie = SessionCookie(
    cookie_name="safecore_session",
    identifier="safecore_verifier",
    # False a propósito: sin cookie devuelve FrontendError y deja que el
    # verificador responda el 303 a /users/login. Con True daría 403 JSON.
    auto_error=False,
    secret_key=os.getenv("SECRET_KEY"),
    cookie_params=cookie_params,
)

# Almacenamiento en MySQL (tabla sesiones): sobrevive reinicios de uvicorn.
# La cookie firmada sigue validando identidad; aquí solo se guarda session_id -> id_usuario.
# Las consultas viven en models/sessionsModel.py; este backend solo orquesta y traduce errores.
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
        # Sin sesión válida el navegador vuelve al login (303, no JSON).
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