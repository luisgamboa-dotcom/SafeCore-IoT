from config.db import get_conn

def get_all_users():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios ORDER BY id_usuario DESC")
    users = cur.fetchall()
    cur.close(); conn.close()
    return users

def create_user(nombre, apellido, email, telefono, password_hash, id_organizacion):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO usuarios (nombre, apellido, email, telefono, password_hash, id_organizacion) VALUES (%s,%s,%s,%s,%s,%s)",
        (nombre, apellido, email, telefono, password_hash, id_organizacion))
    conn.commit()
    cur.close(); conn.close()

def get_user_by_email(email):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios WHERE email = %s",
                (email,)
                )
    user = cur.fetchone()
    cur.close(); conn.close()
    return user

def get_user_by_id(id_usuario):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios WHERE id_usuario = %s",
                (id_usuario,)
                )
    user = cur.fetchone()
    cur.close(); conn.close()
    return user

def update_user(id_usuario, nombre, apellido, email, telefono, password_hash, id_organizacion):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE usuarios SET nombre=%s, apellido=%s, email=%s, telefono=%s, id_organizacion=%s WHERE id_usuario=%s",
        (nombre, apellido, email, telefono, id_organizacion, id_usuario))
    conn.commit()
    cur.close(); conn.close()