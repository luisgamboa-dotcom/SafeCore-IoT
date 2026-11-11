from config.dbConfig import getConnection
from utils.db import closeConnection


def getAllOrganizations(solo_activas=False):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_organizacion, nombre, descripcion, activa FROM organizaciones"
                    + (" WHERE activa = 1" if solo_activas else "")
                    + " ORDER BY nombre")
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getOrganizationById(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_organizacion, nombre, descripcion, activa,"
                    " es_premium, fecha_premium"
                    " FROM organizaciones WHERE id_organizacion = %s",
                    (id_organizacion,))
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def getPlanOrganizacion(id_organizacion):
    """Plan de suscripcion de la organizacion: True = premium, False = gratis."""
    org = getOrganizationById(id_organizacion)
    return bool(org and org.get("es_premium"))


def setPlanOrganizacion(id_organizacion, es_premium):
    """Activa (1) o desactiva (0) el plan premium de la organizacion."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE organizaciones SET es_premium = %s,"
                    " fecha_premium = CASE WHEN %s = 1 THEN NOW() ELSE NULL END"
                    " WHERE id_organizacion = %s",
                    (int(bool(es_premium)), int(bool(es_premium)),
                     id_organizacion))
        conn.commit()
        return cur.rowcount > 0
    finally:
        closeConnection(conn, cur)


def countOrganizationRelations(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT (SELECT COUNT(*) FROM usuarios WHERE id_organizacion = %s)"
                    " + (SELECT COUNT(*) FROM instalaciones WHERE id_organizacion = %s) AS total",
                    (id_organizacion, id_organizacion))
        row = cur.fetchone()
        return row["total"] if row else 0
    finally:
        closeConnection(conn, cur)


def deactivateOrganization(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE organizaciones SET activa = 0 WHERE id_organizacion = %s",
                    (id_organizacion,))
        conn.commit()
    finally:
        closeConnection(conn, cur)


def createOrganization(nombre, descripcion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO organizaciones (nombre, descripcion) VALUES (%s, %s)",
                    (nombre, descripcion))
        conn.commit()
        return cur.lastrowid
    finally:
        closeConnection(conn, cur)


def updateOrganization(id_organizacion, nombre, descripcion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE organizaciones SET nombre = %s, descripcion = %s WHERE id_organizacion = %s",
                    (nombre, descripcion, id_organizacion))
        conn.commit()
    finally:
        closeConnection(conn, cur)


def deleteOrganization(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM organizaciones WHERE id_organizacion = %s", (id_organizacion,))
        conn.commit()
    finally:
        closeConnection(conn, cur)


def forceDeleteOrganization(id_organizacion):
    from models import installationsModel as inst_model
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_instalacion FROM instalaciones WHERE id_organizacion = %s",
                    (id_organizacion,))
        instalaciones = cur.fetchall()
    finally:
        closeConnection(conn, cur)
    for inst in instalaciones:
        inst_model.forceDeleteInstallation(inst["id_instalacion"])
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET id_organizacion = NULL WHERE id_organizacion = %s",
                    (id_organizacion,))
        cur.execute("DELETE FROM organizaciones WHERE id_organizacion = %s", (id_organizacion,))
        conn.commit()
        return True
    finally:
        closeConnection(conn, cur)
