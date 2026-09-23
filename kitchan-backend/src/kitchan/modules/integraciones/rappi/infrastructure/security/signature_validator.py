"""Infraestructura de Rappi: validación de la firma que Rappi envía en cada
webhook, en el header `Rappi-Signature: t=<timestamp>,sign=<hex>`.

Es parecido al HMAC de Uber (ver
integraciones/uber/infrastructure/security/hmac_validator.py), con una
diferencia: Rappi no firma solo el body, firma "<timestamp>.<body>". El
secreto es el que Rappi devuelve al crear el webhook (RAPPI_WEBHOOK_SECRET).
"""

import hashlib
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, Request


def _parsear_header(signature_header: str) -> Optional[tuple[str, str]]:
    """Extrae (t, sign) de "t=123456,sign=abc...". None si falta alguno."""
    partes: dict[str, str] = {}
    for fragmento in signature_header.split(","):
        clave, separador, valor = fragmento.strip().partition("=")
        if separador:
            partes[clave] = valor
    if "t" not in partes or "sign" not in partes:
        return None
    return partes["t"], partes["sign"]


def verify_rappi_signature(secret: str, raw_body: bytes, signature_header: str) -> bool:
    """Verifica la firma HMAC-SHA256 de Rappi sobre "<t>.<body>"."""
    if not secret or not signature_header:
        return False

    parseado = _parsear_header(signature_header)
    if parseado is None:
        return False
    timestamp, firma_recibida = parseado

    mensaje = timestamp.encode("utf-8") + b"." + raw_body
    firma_esperada = hmac.new(
        key=secret.encode("utf-8"), msg=mensaje, digestmod=hashlib.sha256
    ).hexdigest()

    # compare_digest en vez de "==" para prevenir timing attacks.
    return hmac.compare_digest(firma_esperada, firma_recibida)


async def validar_firma_rappi(
    request: Request,
    rappi_signature: Optional[str] = Header(
        default=None, description="Firma HMAC enviada por Rappi"
    ),
) -> bytes:
    """Dependencia de FastAPI: valida la firma y retorna el body crudo."""
    if not rappi_signature:
        raise HTTPException(status_code=401, detail="Firma de Rappi faltante")

    secret = os.getenv("RAPPI_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(
            status_code=500, detail="Falta configurar RAPPI_WEBHOOK_SECRET"
        )

    raw_body = await request.body()

    if not verify_rappi_signature(secret, raw_body, rappi_signature):
        print("🚨 ALERTA: Intento de webhook de Rappi falsificado detectado.")
        raise HTTPException(status_code=403, detail="Firma de Rappi inválida")

    return raw_body
