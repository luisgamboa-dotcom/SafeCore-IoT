from config.db import get_conn
import mysql.connector

# tipo del puente -> magnitud a guardar. El gas se guarda en ADC crudo:
# Python/FastAPI NO convierten a ppm en esta etapa (decision del equipo).
MAGNITUDES = {
    "gas": {"nombre": "MQ-2 ADC crudo", "unidad": "adc", "simbolo": "adc"},
    "temp": {"nombre": "Temperatura", "unidad": "C", "simbolo": "C"},
    "hum": {"nombre": "Humedad", "unidad": "%", "simbolo": "%"},
}


def ensure_magnitud(nombre, unidad, simbolo):
    conn = get_conn()
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


def get_dispositivo_por_serial(codigo_serial):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id_dispositivo, codigo_serial FROM dispositivos WHERE codigo_serial = %s",
        (codigo_serial,),
    )
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def ensure_sensor_para_magnitud(id_dispositivo, id_magnitud):
    """Un sensor por (dispositivo, magnitud). Devuelve id_sensor."""
    conn = get_conn()
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


def insertar_lectura(valor, calidad, mensaje_id, id_sensor, id_magnitud):
    """Retorna {'duplicada': bool, 'id_lectura': int|None}."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO lecturas (valor, calidad, mensaje_id, id_sensor, id_magnitud)"
            " VALUES (%s, %s, %s, %s, %s)",
            (valor, calidad, mensaje_id, id_sensor, id_magnitud),
        )
        conn.commit()
        lid = cur.lastrowid
        cur.close(); conn.close()
        return {"duplicada": False, "id_lectura": lid}
    except mysql.connector.Error as e:
        cur.close(); conn.close()
        if e.errno == 1062:  # mensaje_id duplicado -> reenvio, no es error
            return {"duplicada": True, "id_lectura": None}
        raise


def touch_dispositivo(id_dispositivo):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE dispositivos SET ultima_comunicacion = NOW() WHERE id_dispositivo = %s",
        (id_dispositivo,),
    )
    conn.commit()
    cur.close(); conn.close()


def get_ultimas(limit=50):
    limit = max(1, min(int(limit), 200))
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT l.id_lectura, l.valor, l.fecha_hora, l.calidad, l.mensaje_id,
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
