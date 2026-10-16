# models/usersModel.py — consultas SQL de la tabla usuarios.
# Usado por controllers/authController.py (registro/login) y
# controllers/usersController.py (listado/detalle/edición).
from config.dbConfig import getConnection


def createUser(nombre, apellido, email, telefono, password_hash, id_organizacion):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO usuarios (nombre, apellido, email, telefono, password_hash, id_organizacion) VALUES (%s,%s,%s,%s,%s,%s)",
        (nombre, apellido, email, telefono, password_hash, id_organizacion))
    conn.commit()
    nuevo_id = cur.lastrowid
    cur.close(); conn.close()
    return nuevo_id


def getRoleIdByName(nombre_rol):
    conn = getConnection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_catalogo_rol FROM catalogo_roles WHERE nombre_rol = %s",
                (nombre_rol,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row["id_catalogo_rol"] if row else None


def assignRole(id_usuario, id_rol):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute("INSERT IGNORE INTO usuarios_roles (id_usuario, id_catalogo_rol) VALUES (%s, %s)",
                (id_usuario, id_rol))
    conn.commit()
    cur.close(); conn.close()


def getUserByEmail(email):
    conn = getConnection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios WHERE email = %s",
                (email,)
                )
    user = cur.fetchone()
    cur.close(); conn.close()
    return user


def getUserById(id_usuario):
    conn = getConnection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios WHERE id_usuario = %s",
                (id_usuario,)
                )
    user = cur.fetchone()
    cur.close(); conn.close()
    return user


def getUserRoles(id_usuario):
    conn = getConnection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT r.nombre_rol FROM usuarios_roles ur
                   JOIN catalogo_roles r ON r.id_catalogo_rol = ur.id_catalogo_rol
                   WHERE ur.id_usuario = %s""",
                (id_usuario,))
    roles = [row["nombre_rol"] for row in cur.fetchall()]
    cur.close(); conn.close()
    return roles


def getAllUsersWithDetails(q=None):
    conn = getConnection()
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
    filas = cur.fetchall()
    cur.close(); conn.close()
    return filas


def updateUser(id_usuario, nombre, apellido, email, id_organizacion, id_estado):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE usuarios SET nombre=%s, apellido=%s, email=%s, id_organizacion=%s, id_usuario_estado=%s WHERE id_usuario=%s",
        (nombre, apellido, email, id_organizacion, id_estado, id_usuario))
    conn.commit()
    cur.close(); conn.close()


def replaceUserRole(id_usuario, id_rol):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute("DELETE FROM usuarios_roles WHERE id_usuario = %s", (id_usuario,))
    cur.execute("INSERT INTO usuarios_roles (id_usuario, id_catalogo_rol) VALUES (%s, %s)",
                (id_usuario, id_rol))
    conn.commit()
    cur.close(); conn.close()


def getAllOrganizations():
    conn = getConnection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_organizacion, nombre FROM organizaciones ORDER BY nombre")
    filas = cur.fetchall()
    cur.close(); conn.close()
    return filas


def getAllRoles():
    conn = getConnection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_catalogo_rol, nombre_rol FROM catalogo_roles ORDER BY nombre_rol")
    filas = cur.fetchall()
    cur.close(); conn.close()
    return filas


def getAllUserStates():
    conn = getConnection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_usuario_estado, nombre FROM usuarios_estados ORDER BY id_usuario_estado")
    filas = cur.fetchall()
    cur.close(); conn.close()
    return filas
