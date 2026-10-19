"""Shared helpers: session header context, DB cleanup and address parsing."""
from config.sessionsConfig import SessionData
from models import usersModel as user_model


def initialsOf(user):
    return user["nombre"][0] + (user["apellido"][0] if user and user["apellido"] else "") if user else ""


def userSessionContext(sesion: SessionData):
    user = user_model.getUserById(sesion.id_usuario)
    return {"logged": user["nombre"] if user else None,
            "iniciales": initialsOf(user),
            "is_admin": "Administrador" in user_model.getUserRoles(sesion.id_usuario),
            "id_usuario": sesion.id_usuario}


def adminContext(sesion: SessionData, user):
    return {"is_admin": True,
            "admin_nombre": user["nombre"] if user else "Admin",
            "iniciales": initialsOf(user), "id_usuario": sesion.id_usuario}


def closeConnection(conn, *cursors):
    for cur in cursors:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
    conn.close()


def addressFromForm(form):
    return {"calle": (form.get("calle") or "").strip(),
            "numero": (form.get("numero") or "").strip(),
            "ciudad": (form.get("ciudad") or "").strip(),
            "region": (form.get("region") or "").strip(),
            "codigo_postal": (form.get("codigo_postal") or "").strip() or None}
