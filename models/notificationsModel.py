"""SQL de notificaciones: mensajes por canal (web/email/telegram) hacia los
usuarios, generados al abrirse una alerta o como avisos generales (HU-021)."""
from config.dbConfig import getConnection
from utils.commonUtils import closeConnection

CANAL_WEB = 1


def crearNotificacion(asunto, contenido, id_usuario_destino,
                      id_canal=CANAL_WEB, id_alerta=None):
    """Un aviso para un usuario concreto (تواند con o sin alerta de origen)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO notificaciones
                       (asunto, contenido, estado_envio, id_alerta,
                        id_usuario_destino, id_canal)
                       VALUES (%s, %s, 'enviado', %s, %s, %s)""",
                    (asunto, contenido, id_alerta, id_usuario_destino, id_canal))
        conn.commit()
        return cur.lastrowid
    finally:
        closeConnection(conn, cur)


def crearNotificacionesDeAlerta(id_alerta, asunto, contenido, id_dispositivo):
    """Se llama al abrirse una alerta: una notificación web (canal 1, estado
    'enviado') para cada usuario de la organización del dispositivo.
    Recibe el dispositivo porque el guard de organización de la regla ya
    garantizó que la alerta es de ese dispositivo."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO notificaciones
                       (asunto, contenido, estado_envio, id_alerta,
                        id_usuario_destino, id_canal)
                       SELECT %s, %s, 'enviado', %s, u.id_usuario, %s
                       FROM usuarios u
                       WHERE u.id_organizacion = (
                           SELECT i.id_organizacion
                           FROM dispositivos d
                           JOIN zonas z ON z.id_zona = d.id_zona
                           JOIN instalaciones i ON i.id_instalacion = z.id_instalacion
                           WHERE d.id_dispositivo = %s)""",
                    (asunto[:200], contenido, id_alerta, CANAL_WEB, id_dispositivo))
        conn.commit()
        return cur.rowcount
    finally:
        closeConnection(conn, cur)


def getNotificacionesUsuario(id_usuario, limite=50, solo_no_leidas=False):
    """Centro de notificaciones (HU-021): mensajes del usuario con el canal,
    el estado de envío y, si la notificación nació de una alerta, sus datos
    para el enlace de origen. Ordenado del más reciente al más antiguo.
    solo_no_leidas=True filtra las aún sin leer."""
    limite = max(1, min(int(limite), 200))
    filtro = " AND n.fecha_leida IS NULL" if solo_no_leidas else ""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"""SELECT n.id_notificacion, n.asunto, n.contenido,
                               n.estado_envio, n.fecha_creacion, n.fecha_leida,
                               n.id_alerta, c.nombre AS canal,
                               a.mensaje_corto AS alerta_mensaje,
                               a.severidad AS alerta_severidad,
                               a.id_estado_alerta AS alerta_estado,
                               e.nombre AS estado_alerta
                        FROM notificaciones n
                        JOIN canales_notificacion c ON c.id_canal = n.id_canal
                        LEFT JOIN alertas a ON a.id_alerta = n.id_alerta
                        LEFT JOIN estados_alerta e
                            ON e.id_estado_alerta = a.id_estado_alerta
                        WHERE n.id_usuario_destino = %s{filtro}
                        ORDER BY n.id_notificacion DESC
                        LIMIT {limite}""",
                    (id_usuario,))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def countNoLeidas(id_usuario):
    """Cantidad de notificaciones sin leer de un usuario (badge de la campana)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""SELECT COUNT(*) FROM notificaciones
                       WHERE id_usuario_destino = %s AND fecha_leida IS NULL""",
                    (id_usuario,))
        return int(cur.fetchone()[0])
    finally:
        closeConnection(conn, cur)


def countUsuario(id_usuario):
    """Total de notificaciones del usuario (todas, leídas y sin leer)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""SELECT COUNT(*) FROM notificaciones
                       WHERE id_usuario_destino = %s""", (id_usuario,))
        return int(cur.fetchone()[0])
    finally:
        closeConnection(conn, cur)


def marcarLeida(id_notificacion, id_usuario):
    """HU-021: registra la fecha de lectura SOLO si la notificación es del
    usuario (guard de dueño) y sigue sin leer. 0 filas = no existe, ya está
    leída o no es tuya."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""UPDATE notificaciones SET fecha_leida = NOW()
                       WHERE id_notificacion = %s AND id_usuario_destino = %s
                         AND fecha_leida IS NULL""",
                    (id_notificacion, id_usuario))
        conn.commit()
        return cur.rowcount > 0
    finally:
        closeConnection(conn, cur)
