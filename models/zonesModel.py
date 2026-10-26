"""SQL de las tablas de zonas."""
from config.dbConfig import getConnection
from utils.commonUtils import closeConnection


def createZone(nombre, descripcion, id_instalacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO zonas (nombre, descripcion, id_instalacion) VALUES (%s, %s, %s)",
                    (nombre, descripcion, id_instalacion))
        conn.commit()
        return cur.lastrowid
    finally:
        closeConnection(conn, cur)


def getZoneById(id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT z.*, i.nombre AS instalacion FROM zonas z"
                    " JOIN instalaciones i ON i.id_instalacion = z.id_instalacion"
                    " WHERE z.id_zona = %s",
                    (id_zona,))
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def getAllZones():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT z.id_zona, z.nombre, z.id_instalacion, i.nombre AS instalacion"
                    " FROM zonas z"
                    " JOIN instalaciones i ON i.id_instalacion = z.id_instalacion"
                    " ORDER BY i.nombre, z.nombre")
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getAllZonesWithCounts():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT z.id_zona, z.nombre, z.descripcion, z.id_instalacion,
                              i.nombre AS instalacion, COUNT(d.id_dispositivo) AS n_dispositivos
                       FROM zonas z
                       JOIN instalaciones i ON i.id_instalacion = z.id_instalacion
                       LEFT JOIN dispositivos d ON d.id_zona = z.id_zona
                       GROUP BY z.id_zona
                       ORDER BY i.nombre, z.nombre""")
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getDevicesByZone(id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT d.id_dispositivo, d.codigo_serial, d.nombre, d.activo,
                              d.ultima_comunicacion, m.nombre_modelo, e.nombre AS estado
                       FROM dispositivos d
                       JOIN modelos_dispositivo m ON m.id_modelo = d.id_modelo
                       JOIN estados_dispositivo e ON e.id_estado_dispositivo = d.id_estado_dispositivo
                       WHERE d.id_zona = %s ORDER BY d.nombre""",
                    (id_zona,))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def countDevicesByZone(id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS total FROM dispositivos WHERE id_zona = %s",
                    (id_zona,))
        row = cur.fetchone()
        return row["total"] if row else 0
    finally:
        closeConnection(conn, cur)


def deleteZone(id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM zonas WHERE id_zona = %s", (id_zona,))
        conn.commit()
    finally:
        closeConnection(conn, cur)


def updateZone(id_zona, nombre, descripcion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE zonas SET nombre = %s, descripcion = %s WHERE id_zona = %s",
                    (nombre, descripcion, id_zona))
        conn.commit()
    finally:
        closeConnection(conn, cur)


def forceDeleteZone(id_zona):
    """BORRADO FORZADO: elimina primero dispositivos + sensores + lecturas."""
    from models import devicesModel as dev_model
    for d in getDevicesByZone(id_zona):
        dev_model.deleteDeviceCascade(d["id_dispositivo"])
    deleteZone(id_zona)
