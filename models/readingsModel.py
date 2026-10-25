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


def matchDeviceBySerial(device_serial, device_id):
    """Resuelve el dispositivo por serial y valida/anota su identificador unico."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id_dispositivo, codigo_serial, identificador_unico"
            " FROM dispositivos WHERE codigo_serial = %s",
            (device_serial,),
        )
        dev = cur.fetchone()
        if dev is None:
            return None
        if device_id is None:
            return dev
        if dev["identificador_unico"] is None:
            cur2 = conn.cursor()
            cur2.execute(
                "UPDATE dispositivos SET identificador_unico = %s"
                " WHERE id_dispositivo = %s AND identificador_unico IS NULL",
                (device_id, dev["id_dispositivo"]),
            )
            conn.commit()
            cur2.close()
            dev["identificador_unico"] = device_id
            return dev
        if dev["identificador_unico"] != device_id:
            return {"conflicto": device_id, **dev}
        return dev
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


def getLatest(limit=50, id_organizacion=None):
    limit = max(1, min(int(limit), 200))
    from models.devicesModel import dispositivosOrganizacion_sql
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        if id_organizacion is None:
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
        else:
            cur.execute(
                f"""SELECT l.id_lectura, l.valor, l.fecha_hora, l.calidad,
                           m.nombre AS magnitud, m.simbolo,
                           d.codigo_serial, d.nombre AS dispositivo
                    FROM lecturas l
                    JOIN magnitudes m ON m.id_magnitud = l.id_magnitud
                    JOIN sensores s ON s.id_sensor = l.id_sensor
                    JOIN dispositivos d ON d.id_dispositivo = s.id_dispositivo
                    WHERE {dispositivosOrganizacion_sql('d.id_dispositivo')}
                    ORDER BY l.id_lectura DESC LIMIT %s""",
                (id_organizacion, limit),
            )
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


_MANG_TIPO = {v["nombre"]: k for k, v in MAGNITUDES.items()}
_MANG_TIPO["Gases inflamables"] = "gas"  # nombre usado por el seed del MQ-2.


def getSerieZona(id_zona, limite=300):
    limite = max(1, min(int(limite), 1000))
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT m.nombre AS magnitud_nom,
                      DATE_FORMAT(l.fecha_hora, '%Y-%m-%d %H:%i') AS minuto,
                      AVG(l.valor) AS promedio, COUNT(*) AS muestras
               FROM lecturas l
               JOIN magnitudes m ON m.id_magnitud = l.id_magnitud
               JOIN sensores s ON s.id_sensor = l.id_sensor
               JOIN dispositivos d ON d.id_dispositivo = s.id_dispositivo
               WHERE d.id_zona = %s
               GROUP BY magnitud_nom, minuto
               ORDER BY minuto DESC, magnitud_nom
               LIMIT %s""",
            (id_zona, limite),
        )
        filas = cur.fetchall()
    finally:
        closeConnection(conn, cur)
    filas.reverse()
    return [{"fecha_hora": f["minuto"], "magnitud": _MANG_TIPO.get(f["magnitud_nom"], f["magnitud_nom"]),
             "valor": float(f["promedio"]), "calidad": "valida", "muestras": f["muestras"]}
            for f in filas]


def getHistoricoPorMagnitud(limite=150, id_organizacion=None):
    limite = max(1, min(int(limite), 1000))
    from models.devicesModel import dispositivosOrganizacion_sql
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        if id_organizacion is None:
            cur.execute(
                """SELECT * FROM (
                       SELECT l.id_lectura, l.valor, l.fecha_hora, l.calidad,
                              m.nombre AS magnitud_nom, m.simbolo,
                              d.codigo_serial, d.nombre AS dispositivo
                       FROM lecturas l
                       JOIN magnitudes m ON m.id_magnitud = l.id_magnitud
                       JOIN sensores s ON s.id_sensor = l.id_sensor
                       JOIN dispositivos d ON d.id_dispositivo = s.id_dispositivo
                       ORDER BY l.id_lectura DESC LIMIT %s
                   ) ult ORDER BY ult.id_lectura ASC""",
                (limite,),
            )
        else:
            cur.execute(
                f"""SELECT * FROM (
                        SELECT l.id_lectura, l.valor, l.fecha_hora, l.calidad,
                               m.nombre AS magnitud_nom, m.simbolo,
                               d.codigo_serial, d.nombre AS dispositivo
                        FROM lecturas l
                        JOIN magnitudes m ON m.id_magnitud = l.id_magnitud
                        JOIN sensores s ON s.id_sensor = l.id_sensor
                        JOIN dispositivos d ON d.id_dispositivo = s.id_dispositivo
                        WHERE {dispositivosOrganizacion_sql('d.id_dispositivo')}
                        ORDER BY l.id_lectura DESC LIMIT %s
                    ) ult ORDER BY ult.id_lectura ASC""",
                (id_organizacion, limite),
            )
        filas = cur.fetchall()
    finally:
        closeConnection(conn, cur)
    return [{"id_lectura": f["id_lectura"], "valor": f["valor"],
             "calidad": f["calidad"], "fecha_hora": str(f["fecha_hora"]),
             "magnitud": _MANG_TIPO.get(f["magnitud_nom"], f["magnitud_nom"]),
             "simbolo": f["simbolo"], "codigo_serial": f["codigo_serial"],
             "dispositivo": f["dispositivo"]} for f in filas]


def updateFirmwareVersion(id_dispositivo, fw):
    """Persiste la version de FW reportada por el nodo (editable desde su PWA)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE dispositivos SET firmware_version = %s"
                    " WHERE id_dispositivo = %s", (fw, id_dispositivo))
        conn.commit()
    finally:
        closeConnection(conn, cur)
