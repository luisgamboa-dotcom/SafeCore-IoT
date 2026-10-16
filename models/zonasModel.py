# models/zonasModel.py — consultas SQL de la tabla zonas.
# Usado por controllers/adminController.py. (HU-028: la edición llegará después.)
from config.dbConfig import getConnection


def _cerrar(conn, *cursores):
    for cur in cursores:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
    conn.close()


def createZona(nombre, descripcion, id_instalacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO zonas (nombre, descripcion, id_instalacion) VALUES (%s, %s, %s)",
                    (nombre, descripcion, id_instalacion))
        conn.commit()
        return cur.lastrowid
    finally:
        _cerrar(conn, cur)


def getZonaById(id_zona):
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
        _cerrar(conn, cur)


def getDevicesByZona(id_zona):
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
        _cerrar(conn, cur)


def countDevicesByZona(id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS total FROM dispositivos WHERE id_zona = %s",
                    (id_zona,))
        row = cur.fetchone()
        return row["total"] if row else 0
    finally:
        _cerrar(conn, cur)


def deleteZona(id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM zonas WHERE id_zona = %s", (id_zona,))
        conn.commit()
    finally:
        _cerrar(conn, cur)
