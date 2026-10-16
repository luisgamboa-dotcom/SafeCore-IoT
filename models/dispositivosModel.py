# models/dispositivosModel.py — consultas SQL de la tabla dispositivos.
# Usado por controllers/lecturasController.py (dashboard y detalle).
from config.dbConfig import getConnection


def _cerrar(conn, *cursores):
    for cur in cursores:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
    conn.close()


def getActiveDevices():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT d.id_dispositivo, d.codigo_serial, d.nombre, d.firmware_version,
                              d.ultima_comunicacion, m.nombre_modelo, e.nombre AS estado,
                              z.nombre AS zona, i.nombre AS instalacion,
                              (SELECT l.valor FROM lecturas l
                                JOIN sensores s ON s.id_sensor = l.id_sensor
                                WHERE s.id_dispositivo = d.id_dispositivo
                                ORDER BY l.id_lectura DESC LIMIT 1) AS ultima_lectura,
                              (SELECT l.fecha_hora FROM lecturas l
                                JOIN sensores s ON s.id_sensor = l.id_sensor
                                WHERE s.id_dispositivo = d.id_dispositivo
                                ORDER BY l.id_lectura DESC LIMIT 1) AS fecha_ultima_lectura
                       FROM dispositivos d
                       JOIN modelos_dispositivo m ON m.id_modelo = d.id_modelo
                       JOIN estados_dispositivo e ON e.id_estado_dispositivo = d.id_estado_dispositivo
                       JOIN zonas z ON z.id_zona = d.id_zona
                       LEFT JOIN instalaciones i ON i.id_instalacion = z.id_instalacion
                       WHERE d.activo = 1 ORDER BY d.nombre""")
        return cur.fetchall()
    finally:
        _cerrar(conn, cur)


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
        _cerrar(conn, cur)
