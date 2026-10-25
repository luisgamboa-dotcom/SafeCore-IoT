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


def getActiveDevices(id_organizacion=None):
    # Identity only: dynamic-looking readings belong to the live buffer (JS tick).
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        params = () if id_organizacion is None else (id_organizacion,)
        cur.execute(f"""SELECT d.id_dispositivo, d.codigo_serial, d.nombre, d.firmware_version,
                               m.nombre_modelo, e.nombre AS estado,
                               z.nombre AS zona, i.nombre AS instalacion
                        FROM dispositivos d
                        JOIN modelos_dispositivo m ON m.id_modelo = d.id_modelo
                        JOIN estados_dispositivo e ON e.id_estado_dispositivo = d.id_estado_dispositivo
                        JOIN zonas z ON z.id_zona = d.id_zona
                        LEFT JOIN instalaciones i ON i.id_instalacion = z.id_instalacion
                        WHERE d.activo = 1
                          {id_organizacion_filter('d.id_dispositivo', id_organizacion)}
                        ORDER BY d.nombre""", params)
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def dispositivosOrganizacion_sql(campo):
    """Subquery de dispositivos (tabla `campos`) filtra por organizacion."""
    return f"""{campo} IN (
                    SELECT d2.id_dispositivo FROM dispositivos d2
                    JOIN zonas z2 ON z2.id_zona = d2.id_zona
                    JOIN instalaciones i2 ON i2.id_instalacion = z2.id_instalacion
                    WHERE i2.id_organizacion = %s)"""


def id_organizacion_filter(campo, id_organizacion):
    return "" if id_organizacion is None else f"AND {dispositivosOrganizacion_sql(campo)}"


def getDevicesByOrganization(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"""SELECT d.id_dispositivo, d.codigo_serial, d.nombre, d.activo, d.id_zona
                        FROM dispositivos d
                        JOIN zonas z ON z.id_zona = d.id_zona
                        JOIN instalaciones i ON i.id_instalacion = z.id_instalacion
                        WHERE i.id_organizacion = %s
                        ORDER BY d.codigo_serial""",
                    (id_organizacion,))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getDeviceDetail(id_dispositivo):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT d.*, m.nombre_modelo, m.fabricante, e.nombre AS estado,
                              z.nombre AS zona, i.id_organizacion, i.nombre AS instalacion
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


def deleteDeviceCascade(id_dispositivo):
    """BORRADO FORZADO: lecturas + sensores (sensores_magnitudes cae en CASCADE)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("DELETE l FROM lecturas l"
                    " JOIN sensores s ON s.id_sensor = l.id_sensor"
                    " WHERE s.id_dispositivo = %s",
                    (id_dispositivo,))
        cur.execute("DELETE FROM sensores WHERE id_dispositivo = %s", (id_dispositivo,))
        cur.execute("DELETE FROM dispositivos WHERE id_dispositivo = %s", (id_dispositivo,))
        conn.commit()
    finally:
        closeConnection(conn, cur)


def getAllDevices():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT d.id_dispositivo, d.codigo_serial, d.identificador_unico,
                              d.nombre, d.firmware_version, d.activo,
                              m.nombre_modelo, e.nombre AS estado,
                              z.nombre AS zona, i.nombre AS instalacion
                       FROM dispositivos d
                       JOIN modelos_dispositivo m ON m.id_modelo = d.id_modelo
                       JOIN estados_dispositivo e ON e.id_estado_dispositivo = d.id_estado_dispositivo
                       JOIN zonas z ON z.id_zona = d.id_zona
                       LEFT JOIN instalaciones i ON i.id_instalacion = z.id_instalacion
                       ORDER BY d.activo DESC, d.codigo_serial""")
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def createDevice(codigo_serial, identificador_unico, nombre, firmware_version,
                 fecha_instalacion, id_modelo, id_estado_dispositivo, id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO dispositivos
               (codigo_serial, identificador_unico, nombre, firmware_version,
                fecha_instalacion, id_modelo, id_estado_dispositivo, id_zona)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (codigo_serial, identificador_unico, nombre, firmware_version,
             fecha_instalacion or None, id_modelo, id_estado_dispositivo, id_zona),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        closeConnection(conn, cur)


def updateDevice(id_dispositivo, codigo_serial, identificador_unico, nombre,
                 firmware_version, fecha_instalacion, id_modelo,
                 id_estado_dispositivo, id_zona, activo):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE dispositivos SET codigo_serial = %s, identificador_unico = %s,
                   nombre = %s, firmware_version = %s, fecha_instalacion = %s,
                   id_modelo = %s, id_estado_dispositivo = %s, id_zona = %s, activo = %s
               WHERE id_dispositivo = %s""",
            (codigo_serial, identificador_unico, nombre, firmware_version,
             fecha_instalacion or None, id_modelo, id_estado_dispositivo, id_zona,
             activo, id_dispositivo),
        )
        conn.commit()
    finally:
        closeConnection(conn, cur)


def getAllModels():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_modelo, nombre_modelo, fabricante"
                    " FROM modelos_dispositivo ORDER BY nombre_modelo")
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getAllDeviceStates():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_estado_dispositivo, nombre FROM estados_dispositivo"
                    " ORDER BY id_estado_dispositivo")
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getDeviceBySerial(codigo_serial):
    """Devuelve el dispositivo activo por codigo_serial (lo usa el nodo IoT)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT d.id_dispositivo, d.codigo_serial, d.identificador_unico,
                              d.nombre, d.firmware_version, d.activo,
                              e.nombre AS estado, m.nombre_modelo, z.nombre AS zona
                       FROM dispositivos d
                       JOIN modelos_dispositivo m ON m.id_modelo = d.id_modelo
                       JOIN estados_dispositivo e ON e.id_estado_dispositivo = d.id_estado_dispositivo
                       JOIN zonas z ON z.id_zona = d.id_zona
                       WHERE d.codigo_serial = %s AND d.activo = 1""",
                    (codigo_serial,))
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)
