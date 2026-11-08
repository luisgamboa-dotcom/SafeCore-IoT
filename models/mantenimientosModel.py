from config.dbConfig import getConnection
from utils.commonUtils import closeConnection

_BASE_SELECT = """SELECT mn.id_mantenimiento, mn.fecha_programada, mn.fecha_ejecucion,
                         mn.estado, mn.resultado, mn.proxima_fecha,
                         t.nombre AS tipo, u.nombre AS responsable_nombre,
                         u.apellido AS responsable_apellido
                  FROM mantenimientos mn
                  JOIN tipos_mantenimiento t ON t.id_tipo_mantenimiento = mn.id_tipo_mantenimiento
                  JOIN usuarios u ON u.id_usuario = mn.id_responsable
                  WHERE mn.id_dispositivo = %s"""


def getUltimoMantenimiento(id_dispositivo):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(_BASE_SELECT + """
                    AND mn.estado = 'ejecutado'
                    ORDER BY mn.fecha_ejecucion DESC, mn.id_mantenimiento DESC
                    LIMIT 1""",
                    (id_dispositivo,))
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def getProximoMantenimiento(id_dispositivo):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(_BASE_SELECT + """
                    AND mn.estado = 'programado'
                    ORDER BY mn.fecha_programada ASC, mn.id_mantenimiento ASC
                    LIMIT 1""",
                    (id_dispositivo,))
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def getMantenimientosByDevice(id_dispositivo, limite=20):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(_BASE_SELECT + """
                    ORDER BY (mn.estado <> 'programado') ASC,
                             IF(mn.estado = 'programado', mn.fecha_programada, '9999-12-31') ASC,
                             mn.fecha_ejecucion DESC,
                             mn.id_mantenimiento DESC
                    LIMIT %s""",
                    (id_dispositivo, max(1, min(int(limite), 50))))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getTiposMantenimiento():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT id_tipo_mantenimiento, nombre FROM tipos_mantenimiento
                       ORDER BY id_tipo_mantenimiento""")
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def createMantenimiento(id_dispositivo, id_tipo, fecha_programada, id_responsable,
                        fecha_ejecucion=None, resultado=None, proxima_fecha=None):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO mantenimientos
                   (fecha_programada, fecha_ejecucion, estado, resultado,
                    proxima_fecha, id_dispositivo, id_responsable, id_tipo_mantenimiento)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (fecha_programada, fecha_ejecucion,
             'ejecutado' if fecha_ejecucion else 'programado',
             resultado, proxima_fecha, id_dispositivo, id_responsable, id_tipo))
        conn.commit()
        return cur.lastrowid
    finally:
        closeConnection(conn, cur)


def getMantenimientoById(id_mantenimiento):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT mn.id_mantenimiento, mn.fecha_programada, mn.fecha_ejecucion,
                      mn.estado, mn.resultado, mn.proxima_fecha,
                      mn.id_dispositivo, mn.id_responsable,
                      t.nombre AS tipo, d.codigo_serial, d.nombre AS dispositivo
               FROM mantenimientos mn
               JOIN tipos_mantenimiento t ON t.id_tipo_mantenimiento = mn.id_tipo_mantenimiento
               JOIN dispositivos d ON d.id_dispositivo = mn.id_dispositivo
               WHERE mn.id_mantenimiento = %s""",
            (id_mantenimiento,))
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def registrarEjecucion(id_mantenimiento, fecha_ejecucion, resultado, proxima_fecha):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE mantenimientos
               SET fecha_ejecucion = %s, resultado = %s, proxima_fecha = %s,
                   estado = 'ejecutado'
               WHERE id_mantenimiento = %s AND estado = 'programado'""",
            (fecha_ejecucion, resultado, proxima_fecha, id_mantenimiento))
        conn.commit()
        return cur.rowcount > 0
    finally:
        closeConnection(conn, cur)


def getPendientesByResponsable(id_responsable, limite=10):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT mn.id_mantenimiento, mn.fecha_programada, mn.id_dispositivo,
                      t.nombre AS tipo, d.nombre AS dispositivo, d.codigo_serial
               FROM mantenimientos mn
               JOIN tipos_mantenimiento t ON t.id_tipo_mantenimiento = mn.id_tipo_mantenimiento
               JOIN dispositivos d ON d.id_dispositivo = mn.id_dispositivo
               WHERE mn.id_responsable = %s AND mn.estado = 'programado'
               ORDER BY mn.fecha_programada ASC
               LIMIT %s""",
            (id_responsable, max(1, min(int(limite), 50))))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)
