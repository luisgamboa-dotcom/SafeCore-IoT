// parche_dispositivos.py — agrégalo al FINAL de models/devicesModel.py
// (SafeCore-IoT/models/devicesModel.py). SIN APLICAR: ver parche-servidor/README.md

from config.dbConfig import getConnection
from utils.commonUtils import closeConnection


def getDeviceBySerial(codigo_serial):
    """Devuelve el dispositivo por codigo_serial (lo usa el nodo IoT)."""
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
