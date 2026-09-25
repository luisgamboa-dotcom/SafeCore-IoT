import phonenumbers
from email_validator import validate_email, EmailNotValidError
from phonenumbers import NumberParseException


def validar_email(email):
    # Valida sintaxis y retorna el correo normalizado
    try:
        # Sin deliverability para no depender del DNS
        email_info = validate_email(email, check_deliverability=False)
        return email_info.normalized, None
    except EmailNotValidError:
        return None, "El correo electrónico no es válido. Revísalo e inténtalo de nuevo."


def validar_telefono_chileno(telefono_raw, pais_defecto="CL"):
    """Valida un teléfono con formato chileno por defecto.

    Acepta "912345678", "+56912345678", con espacios/guiones/paréntesis.
    Retorna (digitos_solo_numeros, None) si es válido, (None, mensaje) si no.
    Vacío -> (None, None) porque el campo es opcional.
    """
    if not telefono_raw or not telefono_raw.strip():
        return None, None
    try:
        numero_parseado = phonenumbers.parse(telefono_raw.strip(), pais_defecto)
        # is_possible_number: largo y prefijo plausibles para Chile (9 dígitos móvil, etc.).
        # No se usa is_valid_number porque su metadata rechaza rangos de prueba como 912345678.
        if not phonenumbers.is_possible_number(numero_parseado):
            return None, "El número de teléfono no es válido para Chile."
        telefono_solo_digitos = phonenumbers.format_number(
            numero_parseado,
            phonenumbers.PhoneNumberFormat.E164
        ).lstrip("+")
        return telefono_solo_digitos, None
    except NumberParseException:
        return None, "El número de teléfono no es válido."


def validar_passwords(password, confirm_password):
    password = password.strip()
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres"
    for i in password:
        if i.isspace():
            return "La contraseña no puede contener espacios"
        elif not i.isprintable():
            return "La contraseña contiene caracteres no imprimibles"
        elif i in ('"', "'", "\\", "--"):
            return "La contraseña no puede contener comillas ni barras invertidas"
        
    if password != confirm_password:
        return "Las contraseñas no coinciden"
    return None
