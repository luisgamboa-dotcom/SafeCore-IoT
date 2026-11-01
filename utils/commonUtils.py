"""Utilidades compartidas: contexto de cabecera de sesión, limpieza de BD y parseo de direcciones."""
from config.sessionsConfig import SessionData
from models import usersModel as user_model


def initialsOf(user):
    return user["nombre"][0] + (user["apellido"][0] if user and user["apellido"] else "") if user else ""


def userSessionContext(sesion: SessionData):
    user = user_model.getUserById(sesion.id_usuario)
    roles = user_model.getUserRoles(sesion.id_usuario)
    return {"logged": user["nombre"] if user else None,
            "iniciales": initialsOf(user),
            "is_admin": "Administrador" in roles or "Superadmin" in roles,
            "id_organizacion": user["id_organizacion"] if user else None,
            "id_usuario": sesion.id_usuario,
            # HU-021: badge de notificaciones sin leer de la campana.
            # 0 ante cualquier fallo: el badge nunca rompe la página.
            "notificaciones_no_leidas": notificacionesNoLeidas(sesion)}


def notificacionesNoLeidas(sesion: SessionData):
    """Contador de notificaciones sin leer del usuario (badge de la campana).
    Import diferido del modelo para no crear ciclos; 0 si la BD no responde."""
    try:
        from models import notificationsModel
        return notificationsModel.countNoLeidas(sesion.id_usuario)
    except Exception:
        return 0


def adminContext(sesion: SessionData, user):
    roles = user_model.getUserRoles(sesion.id_usuario)
    return {"is_admin": True,
            "is_superadmin": "Superadmin" in roles,
            "admin_nombre": user["nombre"] if user else "Admin",
            "admin_roles": roles,
            "id_organizacion": user["id_organizacion"] if user else None,
            "iniciales": initialsOf(user), "id_usuario": sesion.id_usuario}


def restrictedOrganization(sesion: SessionData):
    """Organizacion que recorta los datos visibles (None = ve todo).
    Solo roles por debajo de Administrador y con organizacion asignada."""
    user = user_model.getUserById(sesion.id_usuario)
    if user is None or user["id_organizacion"] is None:
        return None
    roles = user_model.getUserRoles(sesion.id_usuario)
    if "Administrador" in roles or "Superadmin" in roles:
        return None
    return user["id_organizacion"]


def dashboardOrganization(sesion: SessionData):
    """Organizacion que acota el dashboard: la del usuario cuando tenga una
    (ve solo sus dispositivos). Usuario comun sin organizacion -> -1 (no ve
    datos de nadie); None solo para administradores sin organizacion (global)."""
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
