# config/sessions.py — sesiones con fastapi-sessions (cookie firmada).
import os
from uuid import UUID

from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi_sessions.backends.session_backend import BackendError, SessionBackend
from fastapi_sessions.frontends.implementations import (
    CookieParameters,
    SessionCookie,
)
from fastapi_sessions.session_verifier import SessionVerifier
from pydantic import BaseModel

from config.db import get_conn

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

# Almacenamiento en MySQL (tabla sesiones): sobrevive reinicios de uvicorn.
# La cookie firmada sigue validando identidad; aquí solo se guarda session_id -> id_usuario.
class MySQLBackend(SessionBackend[UUID, SessionData]):
    async def create(self, session_id: UUID, data: SessionData):
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id_sesion FROM sesiones WHERE id_sesion = %s", (str(session_id),))
            if cur.fetchone():
                raise BackendError("create can't overwrite an existing session")
            cur.execute("INSERT INTO sesiones (id_sesion, id_usuario) VALUES (%s, %s)",
                        (str(session_id), data.id_usuario))
            conn.commit()
            cur.close()
        finally:
            conn.close()

    async def read(self, session_id: UUID):
        conn = get_conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id_usuario FROM sesiones WHERE id_sesion = %s", (str(session_id),))
            row = cur.fetchone()
            cur.close()
        finally:
            conn.close()
        if not row:
            return None
        return SessionData(id_usuario=row["id_usuario"])

    async def update(self, session_id: UUID, data: SessionData) -> None:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE sesiones SET id_usuario = %s WHERE id_sesion = %s",
                        (data.id_usuario, str(session_id)))
            if cur.rowcount == 0:
                raise BackendError("session does not exist, cannot update")
            conn.commit()
            cur.close()
        finally:
            conn.close()

    async def delete(self, session_id: UUID) -> None:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM sesiones WHERE id_sesion = %s", (str(session_id),))
            conn.commit()
            cur.close()
        finally:
            conn.close()


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
