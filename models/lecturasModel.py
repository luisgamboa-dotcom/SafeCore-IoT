from config.dbConfig import getConnection
import mysql.connector

# tipo del puente -> magnitud a guardar. El gas se guarda en ADC crudo:
# Python/FastAPI NO convierten a ppm en esta etapa (decision del equipo).
MAGNITUDES = {
    "gas": {"nombre": "MQ-2 ADC crudo", "unidad": "adc", "simbolo": "adc"},
    "temp": {"nombre": "Temperatura", "unidad": "C", "simbolo": "C"},
    "hum": {"nombre": "Humedad", "unidad": "%", "simbolo": "%"},
}


def ensureMagnitude(nombre, unidad, simbolo):
    conn = getConnection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_magnitud FROM magnitudes WHERE nombre = %s", (nombre,))
    row = cur.fetchone()
    if row:
        cur.close(); conn.close()
        return row["id_magnitud"]
    cur2 = conn.cursor()
    cur2.execute(
        "INSERT INTO magnitudes (nombre, unidad, simbolo) VALUES (%s, %s, %s)",
        (nombre, unidad, simbolo),
    )
    conn.commit()
    new_id = cur2.lastrowid
    cur2.close(); cur.close(); conn.close()
    return new_id


def getDeviceBySerial(codigo_serial):
    conn = getConnection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id_dispositivo, codigo_serial FROM dispositivos WHERE codigo_serial = %s",
        (codigo_serial,),
    )
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def ensureSensorForMagnitude(id_dispositivo, id_magnitud):
    """Un sensor por (dispositivo, magnitud). Devuelve id_sensor."""
    conn = getConnection()
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
        cur.close(); conn.close()
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
    cur2.close(); cur.close(); conn.close()
    return sid


def insertReading(valor, calidad, id_sensor, id_magnitud):
    """Retorna {'id_lectura': int}. Sin mensaje_id (nuevo esquema): no hay deduplicación."""
    conn = getConnection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO lecturas (valor, calidad, id_sensor, id_magnitud)"
        " VALUES (%s, %s, %s, %s)",
        (valor, calidad, id_sensor, id_magnitud),
    )
    conn.commit()
    lid = cur.lastrowid
    cur.close(); conn.close()
    return {"id_lectura": lid}


def touchDevice(id_dispositivo):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE dispositivos SET ultima_comunicacion = NOW() WHERE id_dispositivo = %s",
        (id_dispositivo,),
    )
    conn.commit()
    cur.close(); conn.close()


def getLatest(limit=50):
    limit = max(1, min(int(limit), 200))
    conn = getConnection()
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
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows
