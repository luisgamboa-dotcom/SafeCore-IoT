"""SQL de auditoria_cambios: una fila por cada campo cambiado en un guardado."""
from config.dbConfig import getConnection
from utils.commonUtils import closeConnection


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
