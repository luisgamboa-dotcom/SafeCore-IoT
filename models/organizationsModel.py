"""SQL de organizaciones."""
from config.dbConfig import getConnection


def _cerrar(conn, *cursores):
    for cur in cursores:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
    conn.close()


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
        _cerrar(conn, cur)


def getOrganizationById(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_organizacion, nombre, descripcion, activa FROM organizaciones WHERE id_organizacion = %s",
                    (id_organizacion,))
        return cur.fetchone()
    finally:
        _cerrar(conn, cur)


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
        _cerrar(conn, cur)


def deactivateOrganization(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE organizaciones SET activa = 0 WHERE id_organizacion = %s",
                    (id_organizacion,))
        conn.commit()
    finally:
        _cerrar(conn, cur)


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
        _cerrar(conn, cur)


def updateOrganization(id_organizacion, nombre, descripcion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE organizaciones SET nombre = %s, descripcion = %s WHERE id_organizacion = %s",
                    (nombre, descripcion, id_organizacion))
        conn.commit()
    finally:
        _cerrar(conn, cur)


def deleteOrganization(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM organizaciones WHERE id_organizacion = %s", (id_organizacion,))
        conn.commit()
    finally:
        _cerrar(conn, cur)


def forceDeleteOrganization(id_organizacion):
    """BORRADO FORZADO: instalaciones (con zonas/dispositivos/lecturas) + usuarios desvinculados."""
    from models import installationsModel as inst_model
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_instalacion FROM instalaciones WHERE id_organizacion = %s",
                    (id_organizacion,))
        instalaciones = cur.fetchall()
    finally:
        _cerrar(conn, cur)
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
        _cerrar(conn, cur)
