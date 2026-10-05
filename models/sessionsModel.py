# models/sessionsModel.py — consultas SQL de la tabla sesiones.
# Usado por config/sessionsConfig.py (backend de fastapi-sessions).
from config.dbConfig import getConnection


def sessionExists(id_sesion):
    conn = getConnection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id_sesion FROM sesiones WHERE id_sesion = %s", (id_sesion,))
        existe = cur.fetchone() is not None
        cur.close()
    finally:
        conn.close()
    return existe


def createSession(id_sesion, id_usuario):
    conn = getConnection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO sesiones (id_sesion, id_usuario) VALUES (%s, %s)",
                    (id_sesion, id_usuario))
        conn.commit()
        cur.close()
    finally:
        conn.close()


def getSessionUserId(id_sesion):
    conn = getConnection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_usuario FROM sesiones WHERE id_sesion = %s", (id_sesion,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    return row["id_usuario"] if row else None


def updateSessionUser(id_sesion, id_usuario):
    conn = getConnection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE sesiones SET id_usuario = %s WHERE id_sesion = %s",
                    (id_usuario, id_sesion))
        filas = cur.rowcount
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return filas


def deleteSession(id_sesion):
    conn = getConnection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM sesiones WHERE id_sesion = %s", (id_sesion,))
        conn.commit()
        cur.close()
    finally:
        conn.close()
