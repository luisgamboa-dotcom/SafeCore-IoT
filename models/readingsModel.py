"""SQL de lecturas, magnitudes y sensores (persistencia de la ingesta)."""
from math import ceil

from config.dbConfig import getConnection
from utils.commonUtils import closeConnection

MAGNITUDES = {
    "gas": {"nombre": "Gases inflamables", "unidad": "partes por millon", "simbolo": "ppm"},
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
            "SELECT id_dispositivo, codigo_serial, activo, id_zona FROM dispositivos"
            " WHERE codigo_serial = %s",
            (codigo_serial,),
        )
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def matchDeviceBySerial(device_serial, device_id):
    """Resuelve el dispositivo por serial y valida/anota su identificador unico.
    Un dispositivo dado de baja (activo=0) se retorna marcado con no_activo y
    sin modificar el registro (HU-014)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id_dispositivo, codigo_serial, activo, identificador_unico"
            " FROM dispositivos WHERE codigo_serial = %s",
            (device_serial,),
        )
        dev = cur.fetchone()
        if dev is None:
            return None
        inactivo = dev["activo"] == 0
        # Solo nodos activos pueden anotar su identificador unico.
        if device_id is not None and not inactivo and dev["identificador_unico"] is None:
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
        if not inactivo and device_id is not None and dev["identificador_unico"] != device_id:
            return {"conflicto": device_id, **dev}
        if inactivo:
            dev = {"no_activo": True, **dev}
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
    """Última comunicación AHORA + estado de vuelta a online (1) si estaba offline."""
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


def getHistoricoPorMagnitud(limite=150, id_organizacion=None, serial=None, horas=None):
    """Serie historica (ultimas `limite` lecturas, mas recientes al final) con
    filtros opcionales: organizacion, serial y ventana de horas (0 = sin ventana)."""
    limite = max(1, min(int(limite), 2000))
    from models.devicesModel import dispositivosOrganizacion_sql
    condiciones, params = [], []
    if id_organizacion is not None:
        condiciones.append(dispositivosOrganizacion_sql('d.id_dispositivo'))
        params.append(id_organizacion)
    if serial:
        condiciones.append("d.codigo_serial = %s")
        params.append(serial)
    if horas is not None and horas > 0:
        condiciones.append("l.fecha_hora >= NOW() - INTERVAL %s HOUR")
        params.append(int(horas))
    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            f"""SELECT * FROM (
                    SELECT l.id_lectura, l.valor, l.fecha_hora, l.calidad,
                           m.nombre AS magnitud_nom, m.simbolo,
                           d.codigo_serial, d.nombre AS dispositivo
                    FROM lecturas l
                    JOIN magnitudes m ON m.id_magnitud = l.id_magnitud
                    JOIN sensores s ON s.id_sensor = l.id_sensor
                    JOIN dispositivos d ON d.id_dispositivo = s.id_dispositivo
                    {where}
                    ORDER BY l.id_lectura DESC LIMIT %s
                ) ult ORDER BY ult.id_lectura ASC""",
            (*params, limite),
        )
        filas = cur.fetchall()
    finally:
        closeConnection(conn, cur)
    return [{"id_lectura": f["id_lectura"], "valor": f["valor"],
             "calidad": f["calidad"], "fecha_hora": str(f["fecha_hora"]),
             "magnitud": _MANG_TIPO.get(f["magnitud_nom"], f["magnitud_nom"]),
             "simbolo": f["simbolo"], "codigo_serial": f["codigo_serial"],
             "dispositivo": f["dispositivo"]} for f in filas]


# Puntos objetivo del grafico: el bucket se calcula para no superarlos.
_PUNTOS_OBJETIVO = 300


def _bucketSegundos(horas, desde=None, hasta=None):
    """Bucket en segundos para cubrir el rango real con ~300 puntos. Se usa el
    rango de datos (no la ventana pedida) para no perder detalle cuando aun
    hay pocos dias de historial."""
    if desde is not None and hasta is not None:
        rango = max(0.0, (hasta - desde).total_seconds())
    elif horas:
        rango = int(horas) * 3600
    else:
        rango = 3600
    if rango <= 0:
        return 60
    return max(60, int(ceil(rango / float(_PUNTOS_OBJETIVO) / 60.0)) * 60)


def _statsSerie(where, params):
    """Minimo, maximo, promedio y total de muestras del periodo completo."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"""SELECT MIN(l.fecha_hora) AS desde, MAX(l.fecha_hora) AS hasta,
                               MIN(l.valor) AS vmin, MAX(l.valor) AS vmax,
                               AVG(l.valor) AS vprom, COUNT(*) AS muestras
                        FROM lecturas l
                        JOIN magnitudes m ON m.id_magnitud = l.id_magnitud
                        JOIN sensores s ON s.id_sensor = l.id_sensor
                        JOIN dispositivos d ON d.id_dispositivo = s.id_dispositivo
                        WHERE {where}""", params)
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def _serieBucket(where, params, bucket, por_organizacion=False):
    """Promedio por bucket temporal. En la vista de organizacion agrega
    tambien cuantos dispositivos aportaron a cada punto."""
    extra = ", COUNT(DISTINCT d.id_dispositivo) AS dispositivos" if por_organizacion else ""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"""SELECT FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(l.fecha_hora) / %s) * %s) AS bucket,
                               AVG(l.valor) AS valor, COUNT(*) AS muestras{extra}
                        FROM lecturas l
                        JOIN magnitudes m ON m.id_magnitud = l.id_magnitud
                        JOIN sensores s ON s.id_sensor = l.id_sensor
                        JOIN dispositivos d ON d.id_dispositivo = s.id_dispositivo
                        WHERE {where}
                        GROUP BY bucket
                        ORDER BY bucket ASC""", (bucket, bucket, *params))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def _respuestaSerie(filas, stats, bucket, magnitud, por_organizacion=False):
    serie = []
    for f in filas:
        item = {"fecha_hora": str(f["bucket"]), "valor": float(f["valor"]),
                "muestras": int(f["muestras"])}
        if por_organizacion:
            item["dispositivos"] = int(f["dispositivos"])
        serie.append(item)
    return {"ok": True, "modo": "bd", "magnitud": magnitud, "bucket_s": bucket,
            "desde": str(stats["desde"]), "hasta": str(stats["hasta"]),
            "stats": {"max": float(stats["vmax"]), "min": float(stats["vmin"]),
                      "prom": float(stats["vprom"]), "muestras": int(stats["muestras"])},
            "serie": serie}


def _respuestaVacia(magnitud):
    return {"ok": True, "modo": "bd", "magnitud": magnitud, "bucket_s": 300,
            "desde": None, "hasta": None,
            "stats": {"max": None, "min": None, "prom": None, "muestras": 0},
            "serie": []}


def getSerieDispositivo(serial, horas=None, magnitud="gas", id_organizacion=None):
    """Serie historica de un dispositivo agrupada por bucket temporal, con
    estadisticas del periodo completo (no solo de los puntos dibujados)."""
    from models.devicesModel import dispositivosOrganizacion_sql
    condiciones = ["d.codigo_serial = %s", "m.nombre = %s"]
    params = [serial, MAGNITUDES[magnitud]["nombre"]]
    if id_organizacion is not None:
        condiciones.append(dispositivosOrganizacion_sql("d.id_dispositivo"))
        params.append(id_organizacion)
    if horas:
        condiciones.append("l.fecha_hora >= NOW() - INTERVAL %s HOUR")
        params.append(int(horas))
    where = " AND ".join(condiciones)
    stats = _statsSerie(where, params)
    if not stats or not stats["muestras"]:
        return _respuestaVacia(magnitud)
    bucket = _bucketSegundos(horas, stats["desde"], stats["hasta"])
    return _respuestaSerie(_serieBucket(where, params, bucket), stats, bucket, magnitud)


def getSerieOrganizacion(horas=None, magnitud="gas", id_organizacion=None):
    """Promedio por bucket de todos los dispositivos activos de la
    organizacion (None = todas), para el grafico de historial."""
    from models.devicesModel import dispositivosOrganizacion_sql
    condiciones = ["d.activo = 1", "m.nombre = %s"]
    params = [MAGNITUDES[magnitud]["nombre"]]
    if id_organizacion is not None:
        condiciones.append(dispositivosOrganizacion_sql("d.id_dispositivo"))
        params.append(id_organizacion)
    if horas:
        condiciones.append("l.fecha_hora >= NOW() - INTERVAL %s HOUR")
        params.append(int(horas))
    where = " AND ".join(condiciones)
    stats = _statsSerie(where, params)
    if not stats or not stats["muestras"]:
        return _respuestaVacia(magnitud)
    bucket = _bucketSegundos(horas, stats["desde"], stats["hasta"])
    filas = _serieBucket(where, params, bucket, por_organizacion=True)
    return _respuestaSerie(filas, stats, bucket, magnitud, por_organizacion=True)


def getReadingsForExport(id_dispositivo, horas=1):
    """Lecturas del dispositivo para el CSV de exportacion (horas=0: todo el
    historial), con nombre de dispositivo, magnitud y calidad por fila."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        if horas and horas > 0:
            filtro = "AND l.fecha_hora >= NOW() - INTERVAL %s HOUR"
            params = (id_dispositivo, horas)
        else:
            filtro = ""
            params = (id_dispositivo,)
        cur.execute(f"""SELECT l.fecha_hora, d.nombre AS dispositivo, d.id_dispositivo,
                               m.nombre AS magnitud, l.valor, l.calidad
                        FROM lecturas l
                        JOIN sensores s ON s.id_sensor = l.id_sensor
                        JOIN dispositivos d ON d.id_dispositivo = s.id_dispositivo
                        JOIN magnitudes m ON m.id_magnitud = l.id_magnitud
                        WHERE s.id_dispositivo = %s {filtro}
                        ORDER BY l.fecha_hora""", params)
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


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
