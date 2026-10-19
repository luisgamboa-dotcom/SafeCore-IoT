"""SQL for users, roles and states."""
from config.dbConfig import getConnection


def _cerrar(conn, *cursores):
    for cur in cursores:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
    conn.close()


def createUser(nombre, apellido, email, telefono, password_hash, id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO usuarios (nombre, apellido, email, telefono, password_hash, id_organizacion) VALUES (%s,%s,%s,%s,%s,%s)",
            (nombre, apellido, email, telefono, password_hash, id_organizacion))
        conn.commit()
        return cur.lastrowid
    finally:
        _cerrar(conn, cur)


def getRoleIdByName(nombre_rol):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_catalogo_rol FROM catalogo_roles WHERE nombre_rol = %s",
                    (nombre_rol,))
        row = cur.fetchone()
        return row["id_catalogo_rol"] if row else None
    finally:
        _cerrar(conn, cur)


def assignRole(id_usuario, id_rol):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("INSERT IGNORE INTO usuarios_roles (id_usuario, id_catalogo_rol) VALUES (%s, %s)",
                    (id_usuario, id_rol))
        conn.commit()
    finally:
        _cerrar(conn, cur)


def getUserByEmail(email):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM usuarios WHERE email = %s",
                    (email,)
                    )
        return cur.fetchone()
    finally:
        _cerrar(conn, cur)


def getUserById(id_usuario):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM usuarios WHERE id_usuario = %s",
                    (id_usuario,)
                    )
        return cur.fetchone()
    finally:
        _cerrar(conn, cur)


def getUserRoles(id_usuario):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT r.nombre_rol FROM usuarios_roles ur
                       JOIN catalogo_roles r ON r.id_catalogo_rol = ur.id_catalogo_rol
                       WHERE ur.id_usuario = %s""",
                    (id_usuario,))
        return [row["nombre_rol"] for row in cur.fetchall()]
    finally:
        _cerrar(conn, cur)


def getAllUsersWithDetails(q=None):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT u.id_usuario, u.nombre, u.apellido, u.email, u.fecha_registro,
                              e.nombre AS estado, GROUP_CONCAT(r.nombre_rol SEPARATOR ', ') AS roles
                       FROM usuarios u
                       JOIN usuarios_estados e ON e.id_usuario_estado = u.id_usuario_estado
                       LEFT JOIN usuarios_roles ur ON ur.id_usuario = u.id_usuario
                       LEFT JOIN catalogo_roles r ON r.id_catalogo_rol = ur.id_catalogo_rol
                       WHERE (%s IS NULL OR u.nombre LIKE %s OR u.apellido LIKE %s OR u.email LIKE %s)
                       GROUP BY u.id_usuario ORDER BY u.id_usuario""",
                    (q, f"%{q}%" if q else None, f"%{q}%" if q else None, f"%{q}%" if q else None))
        return cur.fetchall()
    finally:
        _cerrar(conn, cur)


def updateUser(id_usuario, nombre, apellido, email, id_organizacion, id_estado):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE usuarios SET nombre=%s, apellido=%s, email=%s, id_organizacion=%s, id_usuario_estado=%s WHERE id_usuario=%s",
            (nombre, apellido, email, id_organizacion, id_estado, id_usuario))
        conn.commit()
    finally:
        _cerrar(conn, cur)


def replaceUserRole(id_usuario, id_rol):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM usuarios_roles WHERE id_usuario = %s", (id_usuario,))
        cur.execute("INSERT INTO usuarios_roles (id_usuario, id_catalogo_rol) VALUES (%s, %s)",
                    (id_usuario, id_rol))
        conn.commit()
    finally:
        _cerrar(conn, cur)


def getUsersByOrganization(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT u.id_usuario, u.nombre, u.apellido, u.email, e.nombre AS estado,
                              GROUP_CONCAT(r.nombre_rol SEPARATOR ', ') AS roles
                       FROM usuarios u
                       JOIN usuarios_estados e ON e.id_usuario_estado = u.id_usuario_estado
                       LEFT JOIN usuarios_roles ur ON ur.id_usuario = u.id_usuario
                       LEFT JOIN catalogo_roles r ON r.id_catalogo_rol = ur.id_catalogo_rol
                       WHERE u.id_organizacion = %s
                       GROUP BY u.id_usuario ORDER BY u.nombre, u.apellido""",
                    (id_organizacion,))
        return cur.fetchall()
    finally:
        _cerrar(conn, cur)


def getUsersOutsideOrganization(id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT id_usuario, nombre, apellido, email FROM usuarios
                       WHERE id_organizacion IS NULL OR id_organizacion != %s
                       ORDER BY nombre, apellido""",
                    (id_organizacion,))
        return cur.fetchall()
    finally:
        _cerrar(conn, cur)


def setUserOrganization(id_usuario, id_organizacion):
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET id_organizacion = %s WHERE id_usuario = %s",
                    (id_organizacion, id_usuario))
        conn.commit()
    finally:
        _cerrar(conn, cur)


def getAllRoles():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_catalogo_rol, nombre_rol FROM catalogo_roles ORDER BY nombre_rol")
        return cur.fetchall()
    finally:
        _cerrar(conn, cur)


def getAllUserStates():
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_usuario_estado, nombre FROM usuarios_estados ORDER BY id_usuario_estado")
        return cur.fetchall()
    finally:
        _cerrar(conn, cur)
