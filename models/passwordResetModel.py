import hashlib
import secrets
import os
from datetime import datetime, timedelta

from config.dbConfig import getConnection
from utils.db import closeConnection

TTL_HORAS = int(os.getenv("RESET_TOKEN_TTL_HOURS") or "1")


def createToken(id_usuario):

    conn = getConnection()
    cur = None
    try:
        token = secrets.token_urlsafe(32)
        cur = conn.cursor()
        cur.execute("DELETE FROM password_reset_tokens WHERE id_usuario = %s",
                    (id_usuario,))
        cur.execute(
            "INSERT INTO password_reset_tokens (id_usuario, token_hash) VALUES (%s, %s)",
            (id_usuario, hashlib.sha256(token.encode()).hexdigest()))
        conn.commit()
        return token
    finally:
        closeConnection(conn, cur)


def getValidToken(token):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id_token, id_usuario, usado, creado_en FROM password_reset_tokens"
            " WHERE token_hash = %s",
            (hashlib.sha256(token.encode()).hexdigest(),))
        fila = cur.fetchone()
        if fila is None or fila["usado"]:
            return None
        if datetime.now() - fila["creado_en"] > timedelta(hours=TTL_HORAS):
            return None
        return fila
    finally:
        closeConnection(conn, cur)


def markUsed(id_token):

    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE password_reset_tokens SET usado = 1 WHERE id_token = %s",
                    (id_token,))
        conn.commit()
    finally:
        closeConnection(conn, cur)
