from config.dbConfig import getConnection
from utils.db import closeConnection


def registrarAuditoria(id_usuario, entidad, registro_id, accion,
                       valor_anterior, valor_nuevo):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO auditoria_cambios
                       (id_usuario, entidad, registro_id, accion,
                        valor_anterior, valor_nuevo)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (id_usuario, entidad, str(registro_id), accion,
                     str(valor_anterior), str(valor_nuevo)))
        conn.commit()
        return cur.lastrowid
    finally:
        closeConnection(conn, cur)


def getCambios(entidad, registro_id, limite=50):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT a.*, u.nombre, u.apellido
                       FROM auditoria_cambios a
                       LEFT JOIN usuarios u ON u.id_usuario = a.id_usuario
                       WHERE a.entidad = %s AND a.registro_id = %s
                       ORDER BY a.id_auditoria DESC
                       LIMIT %s""",
                    (entidad, str(registro_id), max(1, min(int(limite), 200))))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def getResumenAuditoria():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT DISTINCT entidad FROM auditoria_cambios ORDER BY entidad")
        entidades = [fila["entidad"] for fila in cur.fetchall()]
        cur.execute("""SELECT DISTINCT u.id_usuario, u.nombre, u.apellido
                       FROM auditoria_cambios a
                       JOIN usuarios u ON u.id_usuario = a.id_usuario
                       ORDER BY u.nombre, u.apellido""")
        usuarios = cur.fetchall()
        return entidades, usuarios
    finally:
        closeConnection(conn, cur)


def consultarAuditoria(entidad=None, registro_id=None, id_usuario=None,
                       desde=None, hasta=None, pagina=1, por_pagina=30):
    desde = desde or None
    hasta = hasta or None
    condiciones = []
    parametros = []
    if entidad:
        condiciones.append("a.entidad = %s")
        parametros.append(entidad)
    if registro_id:
        condiciones.append("a.registro_id = %s")
        parametros.append(str(registro_id))
    if id_usuario:
        condiciones.append("a.id_usuario = %s")
        parametros.append(int(id_usuario))
    if desde:
        condiciones.append("a.fecha >= %s")
        parametros.append(f"{desde} 00:00:00")
    if hasta:
        condiciones.append("a.fecha <= %s")
        parametros.append(f"{hasta} 23:59:59")
    filtro_donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"""SELECT COUNT(*) AS total FROM auditoria_cambios a {filtro_donde}""",
                    tuple(parametros))
        total = int(cur.fetchone()["total"])
        pagina = max(1, int(pagina))
        por_pagina = max(1, min(int(por_pagina), 200))
        offset = (pagina - 1) * por_pagina
        cur.execute(f"""SELECT a.id_auditoria, a.id_usuario, a.entidad,
                               a.registro_id, a.accion, a.valor_anterior,
                               a.valor_nuevo, a.fecha,
                               u.nombre, u.apellido
                        FROM auditoria_cambios a
                        LEFT JOIN usuarios u ON u.id_usuario = a.id_usuario
                        {filtro_donde}
                        ORDER BY a.fecha DESC, a.id_auditoria DESC
                        LIMIT {por_pagina} OFFSET {offset}""",
                    tuple(parametros))
        filas = cur.fetchall()
        return filas, total
    finally:
        closeConnection(conn, cur)
