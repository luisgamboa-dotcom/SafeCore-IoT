"""SQL de reglas_alerta: CRUD de reglas de alerta por zona y evaluación de
incumplimientos de las lecturas guardadas. Severidades y operadores son catálogos fijos."""
from datetime import datetime
from decimal import Decimal, InvalidOperation

from config.dbConfig import getConnection
from utils.commonUtils import closeConnection

OPERADORES = (">", ">=", "<", "<=", "=", "!=")
SEVERIDADES = ("baja", "media", "alta", "critica")
MAX_DURACION_S = 7 * 24 * 60 * 60


def getMagnitudes():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_magnitud, nombre, unidad FROM magnitudes ORDER BY id_magnitud")
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getZoneRules(id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT r.*, m.nombre AS magnitud, m.unidad
                       FROM reglas_alerta r
                       JOIN magnitudes m ON m.id_magnitud = r.id_magnitud
                       WHERE r.id_zona = %s
                       ORDER BY m.nombre, r.severidad""",
                    (id_zona,))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getRuleById(id_regla):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM reglas_alerta WHERE id_regla = %s", (id_regla,))
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def createRule(operador, valor_umbral, severidad, duracion_minima_seg,
               vigencia_desde, vigencia_hasta, activa, id_magnitud, id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO reglas_alerta
                       (operador, valor_umbral, severidad, duracion_minima_seg,
                        vigencia_desde, vigencia_hasta, activa, id_magnitud, id_zona)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (operador, valor_umbral, severidad, duracion_minima_seg,
                     vigencia_desde, vigencia_hasta, 1 if activa else 0,
                     id_magnitud, id_zona))
        conn.commit()
        return cur.lastrowid
    finally:
        closeConnection(conn, cur)


def updateRule(id_regla, operador, valor_umbral, severidad, duracion_minima_seg,
               vigencia_desde, vigencia_hasta, activa, id_magnitud):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""UPDATE reglas_alerta
                       SET operador = %s, valor_umbral = %s, severidad = %s,
                           duracion_minima_seg = %s, vigencia_desde = %s,
                           vigencia_hasta = %s, activa = %s, id_magnitud = %s
                       WHERE id_regla = %s""",
                    (operador, valor_umbral, severidad, duracion_minima_seg,
                     vigencia_desde, vigencia_hasta, 1 if activa else 0,
                     id_magnitud, id_regla))
        conn.commit()
    finally:
        closeConnection(conn, cur)


def deleteRule(id_regla):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM reglas_alerta WHERE id_regla = %s", (id_regla,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        closeConnection(conn, cur)


def getActiveRulesOfZone(id_zona):
    """Reglas activas Y dentro de su ventana de vigencia al momento de la llamada."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT r.*, m.nombre AS magnitud
                       FROM reglas_alerta r
                       JOIN magnitudes m ON m.id_magnitud = r.id_magnitud
                       WHERE r.id_zona = %s AND r.activa = 1
                         AND (r.vigencia_desde IS NULL OR r.vigencia_desde <= NOW())
                         AND (r.vigencia_hasta IS NULL OR r.vigencia_hasta >= NOW())""",
                    (id_zona,))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getZoneDevices(id_zona):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_dispositivo, nombre, codigo_serial FROM dispositivos"
                    " WHERE id_zona = %s AND activo = 1", (id_zona,))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getRecentReadingsForMagnitud(id_dispositivo, id_magnitud, segundos):
    """Lecturas de los sensores del dispositivo para una magnitud, de la más antigua
    a la más reciente, dentro de la última ventana de `segundos` (máximo 200 filas)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT l.id_lectura, l.valor, l.fecha_hora
                       FROM lecturas l
                       JOIN sensores s ON s.id_sensor = l.id_sensor
                       JOIN sensores_magnitudes sm
                            ON sm.id_sensor = s.id_sensor
                           AND sm.id_magnitud = l.id_magnitud
                       WHERE s.id_dispositivo = %s AND l.id_magnitud = %s
                         AND l.fecha_hora >= NOW() - INTERVAL %s SECOND
                       ORDER BY l.fecha_hora DESC, l.id_lectura DESC
                       LIMIT 200""",
                    (id_dispositivo, id_magnitud, max(1, int(segundos))))
        filas = cur.fetchall()
        filas.reverse()
        return filas
    finally:
        closeConnection(conn, cur)


def evaluateZone(id_zona):
    """Recalcula el estado de alertas de cada dispositivo activo de la zona con
    las reglas vigentes; crea alertas pendientes y resuelve las abiertas."""
    reglas = getActiveRulesOfZone(id_zona)
    dispositivos = getZoneDevices(id_zona)
    for dev in dispositivos:
        for regla in reglas:
            evaluateDeviceRule(dev, regla)


def evaluateDeviceRule(dev, regla):
    now = datetime.now()
    ventana_msg = max(int(regla["duracion_minima_seg"]), 60) + 3600
    lecturas = getRecentReadingsForMagnitud(dev["id_dispositivo"],
                                            regla["id_magnitud"], ventana_msg)
    if not lecturas:
        return
    umbral = Decimal(str(regla["valor_umbral"]))
    operador = regla["operador"]
    incumple = [_cumples(valor, operador, umbral) for valor in
                (row["valor"] for row in lecturas)]
    # Racha de incumplimiento final: lecturas consecutivas incumpliendo hasta la última.
    racha = 1 if incumple[-1] else 0
    while racha < len(lecturas) and incumple[-(racha + 1)]:
        racha += 1
    if racha == 0:
        # Sin incumplimiento en la última lectura: cualquier alerta abierta de esta regla se resuelve.
        alerta = getOpenAlertaFor(regla["id_regla"], dev["id_dispositivo"])
        if alerta is not None:
            from models import alertsModel
            alertsModel.resolveAlerta(alerta["id_alerta"])
        return
    inicio_racha = lecturas[-racha]["fecha_hora"]
    sostenido = (now - inicio_racha).total_seconds() >= int(regla["duracion_minima_seg"])
    if sostenido:
        alerta = getOpenAlertaFor(regla["id_regla"], dev["id_dispositivo"])
        if alerta is None:
            abrirAlerta(dev, regla, lecturas[-1], int(
                (now - inicio_racha).total_seconds()))
    # Hay incumplimiento pero aún no es sostenido: no tocar las alertas abiertas.


def _cumples(valor, operador, umbral):
    valor = Decimal(str(valor))
    if operador == ">":
        return valor > umbral
    if operador == ">=":
        return valor >= umbral
    if operador == "<":
        return valor < umbral
    if operador == "<=":
        return valor <= umbral
    if operador == "=":
        return valor == umbral
    return valor != umbral


def getOpenAlertaFor(id_regla, id_dispositivo):
    """Import-free helper kept local: pending (1) or acknowledged (2) alert."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT id_alerta, id_estado_alerta FROM alertas
                       WHERE id_regla = %s AND id_dispositivo = %s
                         AND id_estado_alerta IN (1, 2)
                       ORDER BY id_alerta DESC LIMIT 1""",
                    (id_regla, id_dispositivo))
        return cur.fetchone()
    finally:
        closeConnection(conn, cur)


def abrirAlerta(dev, regla, lectura, segundos_sostenido):
    """Import diferido para evitar la importación circular alertsModel/rulesModel."""
    from models import alertsModel
    nombre_magnitud, unidad = alertsModel.magnitudInfo(regla["id_magnitud"])
    sufijo = f" {unidad}" if unidad else ""
    mensaje_corto = (f"{nombre_magnitud} {regla['operador']} "
                     f"{regla['valor_umbral']}{sufijo} en "
                     f"{dev['nombre']} ({dev['codigo_serial']})")
    detalle = (f"Ultima lectura {lectura['valor']}{sufijo} el "
               f"{lectura['fecha_hora']}. Incumplimiento sostenido por "
               f"{segundos_sostenido} segundos.")
    alertsModel.createAlerta(mensaje_corto, detalle, regla["severidad"],
                             regla["id_regla"], lectura["id_lectura"],
                             dev["id_dispositivo"], regla["id_zona"])
