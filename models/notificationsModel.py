"""SQL de notificaciones: mensajes por canal (web/email/telegram) hacia los
usuarios, generados al abrirse una alerta o como avisos generales (HU-021).
HU-022: cada usuario recibe por sus canales habilitados en usuarios_canales."""
from config.dbConfig import getConnection
from utils.commonUtils import closeConnection

CANAL_WEB = 1
CANAL_EMAIL = 2
_CANALES_PERFIL = (CANAL_WEB, CANAL_EMAIL)


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
    """Se llama al abrirse una alerta (HU-017 + HU-022): por cada usuario de
    la organización del dispositivo crea una notificación por cada canal
    habilitado en usuarios_canales (web/email); sin configuración previa
    queda el web por defecto. Los canales email además disparan el correo
    SMTP fuera de la transacción: 'enviado' si salió, 'error' si falló.
    Recibe el dispositivo porque el guard de organización de la regla ya
    garantizó que la alerta es de ese dispositivo."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT u.id_usuario, u.email, uc.id_canal, uc.destino, uc.prioridad
                       FROM usuarios u
                       LEFT JOIN usuarios_canales uc
                            ON uc.id_usuario = u.id_usuario
                           AND uc.habilitado = 1
                           AND uc.id_canal IN (%s, %s)
                       WHERE u.id_usuario_estado = 1
                         AND u.id_organizacion = (
                           SELECT i.id_organizacion
                           FROM dispositivos d
                           JOIN zonas z ON z.id_zona = d.id_zona
                           JOIN instalaciones i ON i.id_instalacion = z.id_instalacion
                           WHERE d.id_dispositivo = %s)""",
                    (CANAL_WEB, CANAL_EMAIL, id_dispositivo))
        por_usuario = {}
        for fila in cur.fetchall():
            if fila["id_canal"] is None:
                # Sin configuracion previa: solo el web por defecto.
                por_usuario.setdefault(fila["id_usuario"], []).append(
                    {"id_usuario": fila["id_usuario"], "email": fila["email"],
                     "id_canal": CANAL_WEB, "destino": None, "prioridad": 1})
            else:
                por_usuario.setdefault(fila["id_usuario"], []).append(
                    {**fila, "email": fila["email"]})
        correos = []
        for canal in [c for objs in por_usuario.values()
                      for c in sorted(objs, key=lambda o: (o["prioridad"], o["id_canal"]))]:
            cur.execute("""INSERT INTO notificaciones
                           (asunto, contenido, estado_envio, id_alerta,
                            id_usuario_destino, id_canal)
                           VALUES (%s, %s, 'pendiente', %s, %s, %s)""",
                        (asunto[:200], contenido, id_alerta,
                         canal["id_usuario"], canal["id_canal"]))
            if canal["id_canal"] == CANAL_WEB:
                cur.execute("""UPDATE notificaciones SET estado_envio = 'enviado'
                               WHERE id_notificacion = %s""", (cur.lastrowid,))
            else:
                correos.append((cur.lastrowid,
                                (canal.get("destino") or "").strip() or canal["email"]))
        conn.commit()
    finally:
        closeConnection(conn, cur)

    for id_notificacion, destino_email in correos:
        estado = "enviado"
        try:
            from utils import emailUtils
            emailUtils.sendAlertaEmail(destino_email, asunto, contenido)
        except Exception:
            estado = "error"
        _actualizarEstadoEnvio(id_notificacion, estado)


def _actualizarEstadoEnvio(id_notificacion, estado):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""UPDATE notificaciones SET estado_envio = %s
                       WHERE id_notificacion = %s""", (estado, id_notificacion))
        conn.commit()
    finally:
        closeConnection(conn, cur)


def getPerfilCanales(id_usuario):
    """HU-022: configuracion web(1)/email(2) del usuario; uc.* NULL significa
    canal sin configurar (el motor lo trata como web por defecto)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT c.id_canal, c.nombre, uc.habilitado, uc.destino, uc.prioridad
                       FROM canales_notificacion c
                       LEFT JOIN usuarios_canales uc
                            ON uc.id_canal = c.id_canal AND uc.id_usuario = %s
                       WHERE c.id_canal IN (%s, %s)
                       ORDER BY c.id_canal""",
                    (id_usuario, CANAL_WEB, CANAL_EMAIL))
        return cur.fetchall()
    finally:
        closeConnection(conn, cur)


def savePerfilCanales(id_usuario, filas):
    """HU-022: reemplazo completo en una sola transaccion del perfil de
    canales web/email del usuario (solo se insertan los habilitados)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""DELETE FROM usuarios_canales
                       WHERE id_usuario = %s AND id_canal IN (%s, %s)""",
                    (id_usuario, CANAL_WEB, CANAL_EMAIL))
        for fila in filas:
            if not fila["habilitado"]:
                continue
            destino = (fila["destino"] or "").strip() or None
            cur.execute("""INSERT INTO usuarios_canales
                           (id_usuario, id_canal, habilitado, destino, prioridad)
                           VALUES (%s, %s, 1, %s, %s)""",
                        (id_usuario, fila["id_canal"], destino, fila["prioridad"]))
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
