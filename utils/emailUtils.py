"""Envio de correo SMTP: restablecimiento (HU-003) y alertas (HU-022)."""
import os
import smtplib
from email.message import EmailMessage

HTML_RESET = """\
<div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px">
  <h2 style="color:#2E1B5A;margin-bottom:4px">SafeCore IoT</h2>
  <h3 style="color:#2E1B5A;margin-top:0">Recuperaci&oacute;n de contrase&ntilde;a</h3>
  <p style="color:#43474e">Hola <b>{nombre}</b>,</p>
  <p style="color:#43474e">Recibimos una solicitud para restablecer la contrase&ntilde;a de tu cuenta.
  Haz clic en el siguiente bot&oacute;n para continuar:</p>
  <p style="text-align:center;margin:24px 0">
    <a href="{enlace}"
       style="background:#6D3DF5;color:#ffffff;padding:12px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold;display:inline-block">
      Restablecer contrase&ntilde;a
    </a>
  </p>
  <p style="color:#43474e">El enlace es temporal y expira en <b>{horas} hora(s)</b>.
  Si no fuiste t&uacute;, ignora este correo y tu clave seguir&aacute; funcionando.</p>
</div>
"""

HTML_ALERTA = """\
<div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px">
  <h2 style="color:#2E1B5A;margin-bottom:4px">SafeCore IoT</h2>
  <h3 style="color:#ba1a1a;margin-top:0">Aviso de seguridad detectado</h3>
  <p style="color:#43474e"><b style="color:#191c1f">{asunto}</b></p>
  <p style="color:#43474e">{contenido}</p>
  <p style="color:#43474e">Revisa el panel de SafeCore IoT para gestionar la alerta.</p>
</div>
"""


def _enviar(msg):
    puerto = int(os.getenv("SMTP_PORT") or "587")
    with smtplib.SMTP(os.getenv("SMTP_HOST") or "smtp.gmail.com", puerto) as smtp:
        smtp.starttls()
        smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        smtp.send_message(msg)


def sendPasswordResetEmail(email_destino, nombre, enlace, horas=1):
    """Envia el correo con el enlace temporal. Lanza excepcion si falla el envio."""
    msg = EmailMessage()
    msg["Subject"] = "Recupera tu contraseña - SafeCore IoT"
    msg["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "safecore-iot@localhost"
    msg["To"] = email_destino
    cuerpo_sin_html = (
        f"Hola {nombre}:\n\n"
        "Recibimos una solicitud para restablecer la contrasena de tu cuenta.\n"
        f"Enlace temporal (expira en {horas} hora(s)):\n"
        f"{enlace}\n\n"
        "Si no fuiste tu, ignora este correo.\n\n"
        "SafeCore IoT")
    msg.set_content(cuerpo_sin_html)
    msg.add_alternative(
        HTML_RESET.format(nombre=nombre, enlace=enlace, horas=horas), subtype="html")
    _enviar(msg)


def sendAlertaEmail(email_destino, asunto, contenido):
    """Envia el correo con el aviso de una alerta (canal email, HU-022)."""
    msg = EmailMessage()
    msg["Subject"] = f"Alerta SafeCore IoT: {asunto}"
    msg["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "safecore-iot@localhost"
    msg["To"] = email_destino
    msg.set_content(
        f"Alerta de seguridad del panel SafeCore IoT:\n\n{asunto}\n\n{contenido}\n\n"
        "Revisa el panel para gestionarla.\n\nSafeCore IoT")
    msg.add_alternative(
        HTML_ALERTA.format(asunto=asunto, contenido=contenido), subtype="html")
    _enviar(msg)
