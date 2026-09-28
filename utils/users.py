import phonenumbers
from email_validator import validate_email, EmailNotValidError
from phonenumbers import NumberParseException


def normalizar_formulario(form_data):
    for key, value in form_data.items():
        form_data[key] = value.strip()
    form_data["nombre"] = form_data["nombre"].capitalize()
    form_data["apellido"] = form_data["apellido"].capitalize()
    return form_data


def validar_email(email):
    # Valida sintaxis y retorna el correo normalizado
    try:
        # Sin deliverability para no depender del DNS
        email_info = validate_email(email, check_deliverability=False)
        return email_info.normalized, None
    except EmailNotValidError:
        return None, "El correo electrónico no es válido. Revísalo e inténtalo de nuevo."


def validar_telefono_chileno(telefono_raw, pais_defecto="CL"):
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
