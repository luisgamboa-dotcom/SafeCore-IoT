# config/sessions.py — sesiones con fastapi-sessions (cookie firmada).
import os
from uuid import UUID

from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi_sessions.backends.implementations import InMemoryBackend
from fastapi_sessions.frontends.implementations import (
    CookieParameters,
    SessionCookie,
)
from fastapi_sessions.session_verifier import SessionVerifier
from pydantic import BaseModel

load_dotenv()


class SessionData(BaseModel):
    # Lo único que viaja en la cookie: el id del usuario logueado
    id_usuario: int


# Cookie de 8 horas (jornada laboral). httponly=True: JS no puede leerla (anti-XSS).
cookie_params = CookieParameters(max_age=8 * 60 * 60)

cookie = SessionCookie(
    cookie_name="safecore_session",
    identifier="safecore_verifier",
    # False a propósito: sin cookie devuelve FrontendError y deja que el
    # verificador responda el 303 a /users/login. Con True daría 403 JSON.
    auto_error=False,
    secret_key=os.getenv("SECRET_KEY", "cambia-esta-clave-en-el-env"),
    cookie_params=cookie_params,
)

# Almacenamiento en memoria del servidor: session_id -> SessionData.
# Se pierde al reiniciar uvicorn (para producción usar backend en MySQL/Redis).
backend: InMemoryBackend[UUID, SessionData] = InMemoryBackend()


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
