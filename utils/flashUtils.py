"""
    Mensajes flash (estilo connect-flash de Node).
    Guarda un mensaje + datos en la sesión, sobrevive UN redirect
    y se borra al leerse. Requiere SessionMiddleware (ver main.py).
    Convención: las claves nunca se flashean ni se repueblan.
"""

CLAVE = "_form_flash"


def flashForm(request, msg, old=None, ok=False):
    # Guarda mensaje global único (+ datos para repoblar, sin claves)
    request.session[CLAVE] = {"msg": msg, "old": old or {}, "ok": ok}


def popFormFlash(request):
    # Lee y borra el flash. Retorna (msg, old, ok)
    datos = request.session.pop(CLAVE, None) or {}
    return datos.get("msg"), datos.get("old", {}), datos.get("ok", False)
