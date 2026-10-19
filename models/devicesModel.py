"""SQL for the dispositivos (devices) tables."""
from config.dbConfig import getConnection
from utils.commonUtils import closeConnection


# 5 minutes without data -> considered powered off (estado forced to offline).
OFFLINE_ID = 2


def markTimedOutDevices():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""UPDATE dispositivos
                       SET id_estado_dispositivo = %s
                       WHERE activo = 1 AND id_estado_dispositivo != %s
                         AND (ultima_comunicacion IS NULL
                              OR ultima_comunicacion < NOW() - INTERVAL 5 MINUTE)""",
                    (OFFLINE_ID, OFFLINE_ID))
        conn.commit()
    finally:
        closeConnection(conn, cur)


def getActiveDevices():
    # Identity only: dynamic-looking readings belong to the live buffer (JS tick).
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT d.id_dispositivo, d.codigo_serial, d.nombre, d.firmware_version,
                              m.nombre_modelo, e.nombre AS estado,
                              z.nombre AS zona, i.nombre AS instalacion
                       FROM dispositivos d
                       JOIN modelos_dispositivo m ON m.id_modelo = d.id_modelo
                       JOIN estados_dispositivo e ON e.id_estado_dispositivo = d.id_estado_dispositivo
                       JOIN zonas z ON z.id_zona = d.id_zona
                       LEFT JOIN instalaciones i ON i.id_instalacion = z.id_instalacion
                       WHERE d.activo = 1 ORDER BY d.nombre""")
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getDeviceDetail(id_dispositivo):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT d.*, m.nombre_modelo, m.fabricante, e.nombre AS estado,
                              z.nombre AS zona, i.nombre AS instalacion
                       FROM dispositivos d
                       JOIN modelos_dispositivo m ON m.id_modelo = d.id_modelo
                       JOIN estados_dispositivo e ON e.id_estado_dispositivo = d.id_estado_dispositivo
                       JOIN zonas z ON z.id_zona = d.id_zona
                       LEFT JOIN instalaciones i ON i.id_instalacion = z.id_instalacion
                       WHERE d.id_dispositivo = %s""",
                    (id_dispositivo,))
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)
