"""Infraestructura de WhatsApp: firma de los mensajes entre el bot y KITCHAN,
en ambos sentidos, con el secreto compartido WHATSAPP_BOT_SECRET.

Header `X-Kitchan-Signature: t=<unix>,sign=<hex>` donde
sign = HMAC-SHA256(secret, "<t>.<body>"). Mismo esquema que Rappi, más una
ventana de tolerancia sobre `t` para que una captura del request no se pueda
reutilizar más tarde.
"""

import hashlib
import hmac
import os
import time
from typing import Optional

from fastapi import Header, HTTPException, Request

HEADER = "X-Kitchan-Signature"
TOLERANCIA_SEGUNDOS = 300


def firmar(secret: str, raw_body: bytes, timestamp: Optional[int] = None) -> str:
    """Valor del header para un body saliente."""
    t = str(int(time.time()) if timestamp is None else timestamp)
    mensaje = t.encode("utf-8") + b"." + raw_body
    sign = hmac.new(secret.encode("utf-8"), mensaje, hashlib.sha256).hexdigest()
    return f"t={t},sign={sign}"


def verificar(
    secret: str,
    raw_body: bytes,
    signature_header: str,
    ahora: Optional[float] = None,
) -> bool:
    if not secret or not signature_header:
        return False
    partes: dict[str, str] = {}
    for fragmento in signature_header.split(","):
        clave, separador, valor = fragmento.strip().partition("=")
        if separador:
            partes[clave] = valor
    if "t" not in partes or "sign" not in partes:
        return False
    try:
        t = int(partes["t"])
    except ValueError:
        return False
    if abs((time.time() if ahora is None else ahora) - t) > TOLERANCIA_SEGUNDOS:
        return False
    esperada = firmar(secret, raw_body, t).partition("sign=")[2]
    return hmac.compare_digest(esperada, partes["sign"])


async def validar_firma_whatsapp(
    request: Request,
    x_kitchan_signature: Optional[str] = Header(
        default=None, description="Firma HMAC enviada por el bot de WhatsApp"
    ),
) -> bytes:
    """Dependencia de FastAPI: valida la firma y retorna el body crudo."""
    if not x_kitchan_signature:
        raise HTTPException(status_code=401, detail="Firma del bot faltante")

    secret = os.getenv("WHATSAPP_BOT_SECRET")
    if not secret:
        raise HTTPException(
            status_code=500, detail="Falta configurar WHATSAPP_BOT_SECRET"
        )

    raw_body = await request.body()
    if not verificar(secret, raw_body, x_kitchan_signature):
        raise HTTPException(status_code=403, detail="Firma del bot inválida")
    return raw_body
