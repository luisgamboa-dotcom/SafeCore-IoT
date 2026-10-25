"""SQL for installations (their address is created/edited with them)."""
# FK fk_zona_inst is CASCADE: deleting an installation with zones would silently remove them.
from config.dbConfig import getConnection
from utils.commonUtils import closeConnection


def getAllInstallations():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT i.id_instalacion, i.nombre, i.descripcion, i.fecha_creacion,
                              o.nombre AS organizacion,
                              CONCAT(d.calle, ' ', d.numero, ', ', d.ciudad) AS direccion,
                              (SELECT COUNT(*) FROM zonas z WHERE z.id_instalacion = i.id_instalacion) AS n_zonas
                       FROM instalaciones i
                       LEFT JOIN organizaciones o ON o.id_organizacion = i.id_organizacion
                       JOIN direcciones d ON d.id_direccion = i.id_direccion
                       ORDER BY i.nombre""")
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getInstallationById(id_instalacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT i.*, o.nombre AS organizacion,
                              d.calle, d.numero, d.ciudad, d.region, d.codigo_postal
                       FROM instalaciones i
                       LEFT JOIN organizaciones o ON o.id_organizacion = i.id_organizacion
                       JOIN direcciones d ON d.id_direccion = i.id_direccion
                       WHERE i.id_instalacion = %s""",
                    (id_instalacion,))
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def getInstallationsByOrganization(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT i.*, d.calle, d.numero, d.ciudad, d.region, d.codigo_postal
                       FROM instalaciones i
                       JOIN direcciones d ON d.id_direccion = i.id_direccion
                       WHERE i.id_organizacion = %s
                       ORDER BY i.nombre""",
                    (id_organizacion,))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getZonesByInstallation(id_instalacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_zona, nombre, descripcion FROM zonas WHERE id_instalacion = %s ORDER BY nombre",
                    (id_instalacion,))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def countZones(id_instalacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS total FROM zonas WHERE id_instalacion = %s",
                    (id_instalacion,))
        row = cur.fetchone()
        return row["total"] if row else 0
    finally:
        closeConnection(conn, cur)


def createInstallation(nombre, descripcion, id_organizacion, calle, numero, ciudad, region, codigo_postal):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO direcciones (calle, numero, ciudad, region, codigo_postal)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    (calle, numero, ciudad, region, codigo_postal or None))
        id_direccion = cur.lastrowid
        cur.execute("INSERT INTO instalaciones (nombre, descripcion, id_direccion, id_organizacion)"
                    " VALUES (%s, %s, %s, %s)",
                    (nombre, descripcion, id_direccion, id_organizacion))
        conn.commit()
        return cur.lastrowid
    finally:
        closeConnection(conn, cur)


def updateInstallation(id_instalacion, nombre, descripcion, id_organizacion,
                       calle, numero, ciudad, region, codigo_postal):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_direccion FROM instalaciones WHERE id_instalacion = %s",
                    (id_instalacion,))
        row = cur.fetchone()
        if row is None:
            return False
        cur.execute("UPDATE direcciones SET calle = %s, numero = %s, ciudad = %s,"
                    " region = %s, codigo_postal = %s WHERE id_direccion = %s",
                    (calle, numero, ciudad, region, codigo_postal or None, row["id_direccion"]))
        cur.execute("UPDATE instalaciones SET nombre = %s, descripcion = %s, id_organizacion = %s"
                    " WHERE id_instalacion = %s",
                    (nombre, descripcion, id_organizacion, id_instalacion))
        conn.commit()
        return True
    finally:
        closeConnection(conn, cur)


def deleteInstallation(id_instalacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_direccion FROM instalaciones WHERE id_instalacion = %s",
                    (id_instalacion,))
        row = cur.fetchone()
        if row is None:
            return False
        cur.execute("DELETE FROM instalaciones WHERE id_instalacion = %s", (id_instalacion,))
        conn.commit()
        cur.execute("DELETE FROM direcciones WHERE id_direccion = %s", (row["id_direccion"],))
        conn.commit()
        return True
    finally:
        closeConnection(conn, cur)


def forceDeleteInstallation(id_instalacion):
    """BORRADO FORZADO: borra las zonas (con sus dispositivos) y la dirección."""
    from models import zonesModel as zone_model
    for z in getZonesByInstallation(id_instalacion):
        zone_model.forceDeleteZone(z["id_zona"])
    return deleteInstallation(id_instalacion)
