"""SQL de alertas: alertas persistidas generadas por la evaluación de reglas."""
from config.dbConfig import getConnection
from utils.commonUtils import closeConnection

PENDIENTE = 1
RECONOCIDA = 2
RESUELTA = 3

# Nombres de catálogo por magnitud, se crea un tipo genérico para magnitudes nuevas.
_TIPO_POR_MAGNITUD = {
    "Gases inflamables": "umbral_gas",
    "Temperatura": "umbral_temperatura",
    "Humedad": "umbral_humedad",
}


def magnitudInfo(id_magnitud):
    """(nombre, unidad) de una magnitud, o sino (None, None)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT nombre, unidad FROM magnitudes WHERE id_magnitud = %s",
                    (id_magnitud,))
        fila = cur.fetchone()
        return (fila["nombre"], fila["unidad"]) if fila is not None else (None, None)
    finally:
        closeConnection(conn, cur)


def _tipoIdPorMagnitud(cur, nombre_magnitud):
    tipo_nombre = _TIPO_POR_MAGNITUD.get(nombre_magnitud)
    if not tipo_nombre and nombre_magnitud:
        tipo_nombre = "umbral_" + nombre_magnitud.lower().replace(" ", "_")
    cur.execute("SELECT id_tipo_alerta FROM tipos_alerta WHERE nombre = %s",
                (tipo_nombre,))
    fila = cur.fetchone()
    if fila is not None:
        return fila["id_tipo_alerta"]
    cur.execute("INSERT INTO tipos_alerta (nombre) VALUES (%s)", (tipo_nombre,))
    return cur.lastrowid


def createAlerta(mensaje_corto, detalle_tecnico, severidad, id_regla,
                 id_lectura, id_dispositivo, id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_magnitud FROM reglas_alerta WHERE id_regla = %s",
                    (id_regla,))
        id_tipo = None
        fila = cur.fetchone()
        if fila is not None:
            cur.execute("SELECT nombre FROM magnitudes WHERE id_magnitud = %s",
                        (fila["id_magnitud"],))
            mag = cur.fetchone()
            if mag is not None:
                id_tipo = _tipoIdPorMagnitud(cur, mag["nombre"])
        if id_tipo is None:
            id_tipo = _tipoIdPorMagnitud(cur, None)
        cur.execute("""INSERT INTO alertas
                       (mensaje_corto, detalle_tecnico, severidad, id_regla,
                        id_lectura_origen, id_dispositivo, id_zona,
                        id_tipo_alerta, id_estado_alerta)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (mensaje_corto, detalle_tecnico, severidad, id_regla,
                     id_lectura, id_dispositivo, id_zona, id_tipo, PENDIENTE))
        conn.commit()
        return cur.lastrowid
    finally:
        closeConnection(conn, cur)


def resolveAlerta(id_alerta):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""UPDATE alertas SET id_estado_alerta = %s,
                       fecha_resolucion = NOW()
                       WHERE id_alerta = %s AND id_estado_alerta IN (1, 2)""",
                    (RESUELTA, id_alerta))
        conn.commit()
        return cur.rowcount > 0
    finally:
        closeConnection(conn, cur)


def getRecentAlerts(id_organizacion=None, limite=10):
    """Últimas alertas registradas, recortadas a los dispositivos de la
    organización cuando se indique (None = todas las organizaciones)."""
    limite = max(1, min(int(limite), 50))
    from models.devicesModel import dispositivosOrganizacion_sql
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        if id_organizacion is not None:
            cur.execute(f"""SELECT a.id_alerta, a.mensaje_corto, a.severidad,
                                   a.fecha_inicio, a.fecha_resolucion,
                                   e.nombre AS estado, d.nombre AS dispositivo,
                                   d.codigo_serial, z.nombre AS zona
                            FROM alertas a
                            JOIN estados_alerta e ON e.id_estado_alerta = a.id_estado_alerta
                            JOIN dispositivos d ON d.id_dispositivo = a.id_dispositivo
                            JOIN zonas z ON z.id_zona = a.id_zona
                            WHERE {dispositivosOrganizacion_sql('a.id_dispositivo')}
                            ORDER BY a.id_alerta DESC
                            LIMIT %s""",
                        (id_organizacion, limite))
        else:
            cur.execute("""SELECT a.id_alerta, a.mensaje_corto, a.severidad,
                                  a.fecha_inicio, a.fecha_resolucion,
                                  e.nombre AS estado, d.nombre AS dispositivo,
                                  d.codigo_serial, z.nombre AS zona
                           FROM alertas a
                           JOIN estados_alerta e ON e.id_estado_alerta = a.id_estado_alerta
                           JOIN dispositivos d ON d.id_dispositivo = a.id_dispositivo
                           JOIN zonas z ON z.id_zona = a.id_zona
                           ORDER BY a.id_alerta DESC
                           LIMIT %s""",
                        (limite,))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getAlertasCompletas(id_organizacion=None, limite=50):
    """Pagina de alertas: todas las alertas de la organizacion con el detalle
    de regla, lectura de origen y quien las reconocio/resolvio
    (None = usuario global -> todas las organizaciones)."""
    limite = max(1, min(int(limite), 200))
    from models.devicesModel import dispositivosOrganizacion_sql
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        sql = """SELECT a.id_alerta, a.mensaje_corto, a.detalle_tecnico,
                        a.severidad, a.fecha_inicio, a.fecha_reconocimiento,
                        a.fecha_resolucion,
                        e.nombre AS estado, t.nombre AS tipo,
                        d.nombre AS dispositivo, d.codigo_serial,
                        z.nombre AS zona,
                        m.nombre AS magnitud, m.unidad,
                        r.operador, r.valor_umbral,
                        l.valor AS valor_origen, l.fecha_hora AS fecha_origen,
                        u1.nombre AS reconoce_nombre, u1.apellido AS reconoce_apellido,
                        u2.nombre AS resuelve_nombre, u2.apellido AS resuelve_apellido
                 FROM alertas a
                 JOIN estados_alerta e ON e.id_estado_alerta = a.id_estado_alerta
                 JOIN dispositivos d ON d.id_dispositivo = a.id_dispositivo
                 JOIN zonas z ON z.id_zona = a.id_zona
                 JOIN tipos_alerta t ON t.id_tipo_alerta = a.id_tipo_alerta
                 JOIN reglas_alerta r ON r.id_regla = a.id_regla
                 JOIN magnitudes m ON m.id_magnitud = r.id_magnitud
                 JOIN lecturas l ON l.id_lectura = a.id_lectura_origen
                 LEFT JOIN usuarios u1 ON u1.id_usuario = a.reconocido_por
                 LEFT JOIN usuarios u2 ON u2.id_usuario = a.resuelto_por"""
        if id_organizacion is not None:
            filtro = f" WHERE {dispositivosOrganizacion_sql('a.id_dispositivo')}"
        else:
            filtro = ""
        cur.execute(f"""{sql}{filtro}
                        ORDER BY a.id_alerta DESC
                        LIMIT {limite}""",
                    (id_organizacion,) if id_organizacion is not None else ())
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def countActiveAlerts(id_organizacion=None):
    """Cantidad de alertas abiertas (pendientes + reconocidas), recortadas por
    organización cuando se indique."""
    from models.devicesModel import dispositivosOrganizacion_sql
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        if id_organizacion is not None:
            cur.execute(f"""SELECT COUNT(*) FROM alertas a
                            WHERE a.id_estado_alerta IN ({PENDIENTE}, {RECONOCIDA})
                              AND {dispositivosOrganizacion_sql('a.id_dispositivo')}""",
                        (id_organizacion,))
        else:
            cur.execute(f"""SELECT COUNT(*) FROM alertas a
                            WHERE a.id_estado_alerta IN ({PENDIENTE}, {RECONOCIDA})""")
        return int(cur.fetchone()[0])
    finally:
        closeConnection(conn, cur)


def cancelarAlertasDeDispositivo(id_dispositivo):
    """HU-014: al dar de baja un dispositivo cancela sus alertas activas
    (pendientes y reconocidas) pasandolas a resuelta."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""UPDATE alertas
                       SET id_estado_alerta = %s, fecha_resolucion = NOW()
                       WHERE id_dispositivo = %s AND id_estado_alerta IN (%s, %s)""",
                    (RESUELTA, id_dispositivo, PENDIENTE, RECONOCIDA))
        conn.commit()
        return cur.rowcount
    finally:
        closeConnection(conn, cur)


def getDeviceAlertas(id_dispositivo):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT a.id_alerta, a.mensaje_corto, a.severidad, a.fecha_inicio,
                              a.fecha_reconocimiento, a.fecha_resolucion,
                              e.nombre AS estado, t.nombre AS tipo,
                              m.nombre AS magnitud, r.operador, r.valor_umbral,
                              m.unidad
                       FROM alertas a
                       JOIN estados_alerta e ON e.id_estado_alerta = a.id_estado_alerta
                       JOIN tipos_alerta t ON t.id_tipo_alerta = a.id_tipo_alerta
                       JOIN reglas_alerta r ON r.id_regla = a.id_regla
                       JOIN magnitudes m ON m.id_magnitud = r.id_magnitud
                       WHERE a.id_dispositivo = %s
                       ORDER BY a.id_alerta DESC
                       LIMIT 50""",
                    (id_dispositivo,))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)
