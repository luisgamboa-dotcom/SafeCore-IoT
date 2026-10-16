"""Mensajes flash: sobreviven UN redirect y se borran al leerse."""

CLAVE = "_form_flash"


def flashForm(request, msg, old=None, ok=False):
    # Guarda mensaje global único mas los datos para repoblar, sin claves
    request.session[CLAVE] = {"msg": msg, "old": old or {}, "ok": ok}


def popFormFlash(request):
    # Lee y borra el flash. Retorna (msg, old, ok)
    datos = request.session.pop(CLAVE, None) or {}
    return datos.get("msg"), datos.get("old", {}), datos.get("ok", False)
