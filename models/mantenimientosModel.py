"""SQL de mantenimientos (mantenimiento de dispositivos). HU-016 solo lee; el CRUD
para registrar mantenimientos pertenece a HU-015."""
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
    """Registro más reciente: primero el ejecutado, si no el programado."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(_BASE_SELECT + """
                    ORDER BY COALESCE(mn.fecha_ejecucion, mn.fecha_programada) DESC,
                             mn.id_mantenimiento DESC
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
                    ORDER BY COALESCE(mn.fecha_ejecucion, mn.fecha_programada) DESC,
                             mn.id_mantenimiento DESC
                    LIMIT %s""",
                    (id_dispositivo, max(1, min(int(limite), 50))))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)
