# models/usersModel.py — consultas SQL de la tabla usuarios.
# Usado por controllers/authController.py (registro/login) y
# controllers/usersController.py (listado/detalle/edición).
from config.dbConfig import getConnection


def getAllUsers():
    conn = getConnection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios ORDER BY id_usuario DESC")
    users = cur.fetchall()
    cur.close(); conn.close()
    return users


def createUser(nombre, apellido, email, telefono, password_hash, id_organizacion):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO usuarios (nombre, apellido, email, telefono, password_hash, id_organizacion) VALUES (%s,%s,%s,%s,%s,%s)",
        (nombre, apellido, email, telefono, password_hash, id_organizacion))
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


def updateUser(id_usuario, nombre, apellido, email, telefono, id_organizacion):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE usuarios SET nombre=%s, apellido=%s, email=%s, telefono=%s, id_organizacion=%s WHERE id_usuario=%s",
        (nombre, apellido, email, telefono, id_organizacion, id_usuario))
    conn.commit()
    cur.close(); conn.close()
