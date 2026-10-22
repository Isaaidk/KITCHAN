"""Adaptadores de salida para enviar correos.

Con SMTP_HOST configurado el correo sale por SMTP. Sin él (desarrollo local) el
código se escribe en el log del servidor, para poder probar el flujo sin correo.
"""

import asyncio
import logging
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from src.kitchan.modules.usuarios.application.ports import IEnviadorCorreo

logger = logging.getLogger(__name__)

REMITENTE_NOMBRE = "Vangalia KITCHAN"


def _texto(nombre: str, codigo: str, minutos: int) -> str:
    return (
        f"Hola {nombre},\n\n"
        f"Tu código para restablecer la contraseña es: {codigo}\n\n"
        f"Vence en {minutos} minutos. Si no lo pediste tú, ignora este correo: "
        "tu contraseña seguirá igual.\n\n"
        "Vangalia KITCHAN"
    )


def _html(nombre: str, codigo: str, minutos: int) -> str:
    return f"""\
<div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#2e3a46">
  <h2 style="color:#6b1e3c;margin:0 0 16px">Restablecer contraseña</h2>
  <p>Hola {nombre},</p>
  <p>Usa este código para crear una contraseña nueva:</p>
  <p style="font-size:32px;font-weight:700;letter-spacing:8px;background:#f8f6ef;
            padding:16px;text-align:center;border-radius:12px;color:#6b1e3c">{codigo}</p>
  <p style="color:#5e6b78;font-size:14px">Vence en {minutos} minutos. Si no lo pediste tú,
  ignora este correo: tu contraseña seguirá igual.</p>
</div>"""


class EnviadorCorreoSMTP(IEnviadorCorreo):
    def __init__(self, host: str, puerto: int, usuario: str, clave: str, remitente: str):
        self.host = host
        self.puerto = puerto
        self.usuario = usuario
        self.clave = clave
        self.remitente = remitente

    async def enviar_codigo_recuperacion(
        self, destinatario: str, nombre: str, codigo: str, minutos_validez: int
    ) -> None:
        mensaje = EmailMessage()
        mensaje["Subject"] = "Tu código para restablecer la contraseña"
        mensaje["From"] = formataddr((REMITENTE_NOMBRE, self.remitente))
        mensaje["To"] = destinatario
        mensaje.set_content(_texto(nombre, codigo, minutos_validez))
        mensaje.add_alternative(_html(nombre, codigo, minutos_validez), subtype="html")
        # smtplib es bloqueante: se manda en un hilo para no frenar el servidor.
        await asyncio.to_thread(self._enviar, mensaje)

    def _enviar(self, mensaje: EmailMessage) -> None:
        if self.puerto == 465:
            servidor = smtplib.SMTP_SSL(self.host, self.puerto, timeout=15)
        else:
            servidor = smtplib.SMTP(self.host, self.puerto, timeout=15)
        with servidor:
            if self.puerto != 465:
                servidor.starttls()
            if self.usuario:
                servidor.login(self.usuario, self.clave)
            servidor.send_message(mensaje)


class EnviadorCorreoConsola(IEnviadorCorreo):
    """Solo para desarrollo: deja el código en el log en vez de enviarlo."""

    async def enviar_codigo_recuperacion(
        self, destinatario: str, nombre: str, codigo: str, minutos_validez: int
    ) -> None:
        logger.warning(
            "SMTP no configurado: código de recuperación para %s = %s (vence en %s min)",
            destinatario,
            codigo,
            minutos_validez,
        )


def construir_enviador_correo() -> IEnviadorCorreo:
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        return EnviadorCorreoConsola()
    usuario = os.getenv("SMTP_USER", "")
    return EnviadorCorreoSMTP(
        host=host,
        puerto=int(os.getenv("SMTP_PORT", "587")),
        usuario=usuario,
        clave=os.getenv("SMTP_PASSWORD", ""),
        remitente=os.getenv("SMTP_FROM", usuario),
    )
