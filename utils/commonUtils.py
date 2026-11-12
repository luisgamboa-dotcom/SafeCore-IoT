from config.sessionsConfig import SessionData


def initialsOf(user):
    if not user:
        return ""
    nombre = (user.get("nombre") or "").strip()
    apellido = (user.get("apellido") or "").strip()
    iniciales = ""
    if nombre:
        iniciales += nombre[0].upper()
    if apellido:
        iniciales += apellido[0].upper()
    return iniciales


def userSessionContext(sesion: SessionData):
    from models import usersModel as user_model
    user = user_model.getUserById(sesion.id_usuario)
    roles = user_model.getUserRoles(sesion.id_usuario)
    es_premium = esUsuarioPremium(sesion)
    return {"logged": user["nombre"] if user else None,
            "iniciales": initialsOf(user),
            "is_admin": "Administrador" in roles or "Superadmin" in roles,
            "id_organizacion": user["id_organizacion"] if user else None,
            "id_usuario": sesion.id_usuario,
            "es_premium": es_premium,


            "notificaciones_no_leidas": notificacionesNoLeidas(sesion) if es_premium else 0}


def esUsuarioPremium(sesion: SessionData) -> bool:
    """Plan de suscripcion efectivo: el propio del usuario en sesion.
    Ante cualquier falla de BD se trata como premium para no bloquear
    el panel."""
    from models import usersModel as user_model
    try:
        user = user_model.getUserById(sesion.id_usuario)
        if user is None:
            return True
        return bool(user["es_premium"])
    except Exception:
        return True


def usuarioOrganizacion(sesion: SessionData):
    """(id_organizacion, es_premium) del usuario en sesion, o (None, True)."""
    from models import usersModel as user_model
    try:
        user = user_model.getUserById(sesion.id_usuario)
        if user is None:
            return None, True
        return user["id_organizacion"], bool(user["es_premium"])
    except Exception:
        return None, True


def notificacionesNoLeidas(sesion: SessionData):
    try:
        from models import notificationsModel
        return notificationsModel.countNoLeidas(sesion.id_usuario)
    except Exception:
        return 0


def adminContext(sesion: SessionData, user):
    from models import usersModel as user_model
    roles = user_model.getUserRoles(sesion.id_usuario)
    return {"is_admin": True,
            "is_superadmin": "Superadmin" in roles,
            "admin_nombre": user["nombre"] if user else "Admin",
            "admin_roles": roles,
            "id_organizacion": user["id_organizacion"] if user else None,
            "iniciales": initialsOf(user), "id_usuario": sesion.id_usuario}


def restrictedOrganization(sesion: SessionData):
    from models import usersModel as user_model
    user = user_model.getUserById(sesion.id_usuario)
    if user is None or user["id_organizacion"] is None:
        return None
    roles = user_model.getUserRoles(sesion.id_usuario)
    if "Administrador" in roles or "Superadmin" in roles:
        return None
    return user["id_organizacion"]


def dashboardOrganization(sesion: SessionData):
    from models import usersModel as user_model
    user = user_model.getUserById(sesion.id_usuario)
    if user is None:
        return -1
    if user["id_organizacion"] is not None:
        return user["id_organizacion"]
    roles = user_model.getUserRoles(sesion.id_usuario)
    if "Administrador" in roles or "Superadmin" in roles:
        return None
    return -1


def organizationSerials(id_organizacion):
    from models import devicesModel as dev_model
    return {d["codigo_serial"] for d in dev_model.getDevicesByOrganization(id_organizacion)}


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


# Re-export for backward compatibility
from utils.db import closeConnection
