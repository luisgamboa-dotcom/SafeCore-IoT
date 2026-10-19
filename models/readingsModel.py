"""SQL for readings, magnitudes and sensors (ingest persistence)."""
from config.dbConfig import getConnection
from utils.commonUtils import closeConnection

MAGNITUDES = {
    "gas": {"nombre": "MQ-2 ADC crudo", "unidad": "adc", "simbolo": "adc"},
    "temp": {"nombre": "Temperatura", "unidad": "C", "simbolo": "C"},
    "hum": {"nombre": "Humedad", "unidad": "%", "simbolo": "%"},
}



def ensureMagnitude(nombre, unidad, simbolo):
    conn = getConnection()
    cur = cur2 = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_magnitud FROM magnitudes WHERE nombre = %s", (nombre,))
        row = cur.fetchone()
        if row:
            return row["id_magnitud"]
        cur2 = conn.cursor()
        cur2.execute(
            "INSERT INTO magnitudes (nombre, unidad, simbolo) VALUES (%s, %s, %s)",
            (nombre, unidad, simbolo),
        )
        conn.commit()
        return cur2.lastrowid
    finally:
        closeConnection(conn, cur, cur2)


def getDeviceBySerial(codigo_serial):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id_dispositivo, codigo_serial FROM dispositivos WHERE codigo_serial = %s",
            (codigo_serial,),
        )
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def ensureSensorForMagnitude(id_dispositivo, id_magnitud):
    conn = getConnection()
    cur = cur2 = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT s.id_sensor FROM sensores s
               JOIN sensores_magnitudes sm ON sm.id_sensor = s.id_sensor
               WHERE s.id_dispositivo = %s AND sm.id_magnitud = %s
               LIMIT 1""",
            (id_dispositivo, id_magnitud),
        )
        row = cur.fetchone()
        if row:
            return row["id_sensor"]
        cur2 = conn.cursor()
        cur2.execute(
            "INSERT INTO sensores (frecuencia_muestreo, habilitado, id_dispositivo)"
            " VALUES (10, 1, %s)",
            (id_dispositivo,),
        )
        conn.commit()
        sid = cur2.lastrowid
        cur2.execute(
            "INSERT IGNORE INTO sensores_magnitudes (id_sensor, id_magnitud) VALUES (%s, %s)",
            (sid, id_magnitud),
        )
        conn.commit()
        return sid
    finally:
        closeConnection(conn, cur, cur2)


def insertReading(valor, calidad, id_sensor, id_magnitud):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO lecturas (valor, calidad, id_sensor, id_magnitud)"
            " VALUES (%s, %s, %s, %s)",
            (valor, calidad, id_sensor, id_magnitud),
        )
        conn.commit()
        return {"id_lectura": cur.lastrowid}
    finally:
        closeConnection(conn, cur)


def touchDevice(id_dispositivo):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE dispositivos SET ultima_comunicacion = NOW() WHERE id_dispositivo = %s",
            (id_dispositivo,),
        )
        conn.commit()
    finally:
        closeConnection(conn, cur)


def markDeviceAlive(id_dispositivo):
    """Last communication NOW + estado back to online (1) if it was offline."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE dispositivos SET ultima_comunicacion = NOW(),"
            " id_estado_dispositivo = 1 WHERE id_dispositivo = %s AND id_estado_dispositivo = 2",
            (id_dispositivo,),
        )
        conn.commit()
    finally:
        closeConnection(conn, cur)


def getLatest(limit=50):
    limit = max(1, min(int(limit), 200))
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT l.id_lectura, l.valor, l.fecha_hora, l.calidad,
                      m.nombre AS magnitud, m.simbolo,
                      d.codigo_serial, d.nombre AS dispositivo
               FROM lecturas l
               JOIN magnitudes m ON m.id_magnitud = l.id_magnitud
               JOIN sensores s ON s.id_sensor = l.id_sensor
               JOIN dispositivos d ON d.id_dispositivo = s.id_dispositivo
               ORDER BY l.id_lectura DESC LIMIT %s""",
            (limit,),
        )
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)
