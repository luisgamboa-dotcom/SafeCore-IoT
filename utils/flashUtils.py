"""Flash messages: survive ONE redirect, deleted on read."""

CLAVE = "_form_flash"


def flashForm(request, msg, old=None, ok=False):
    request.session[CLAVE] = {"msg": msg, "old": old or {}, "ok": ok}


def popFormFlash(request):
    datos = request.session.pop(CLAVE, None) or {}
    return datos.get("msg"), datos.get("old", {}), datos.get("ok", False)

