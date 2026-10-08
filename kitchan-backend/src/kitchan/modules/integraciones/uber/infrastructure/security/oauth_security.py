import hmac
import hashlib
import os
from fastapi import Request, HTTPException, Header
from typing import Optional

# En un entorno real, esto viene de tus variables de entorno (.env)
# Le pongo tu clave generada como valor por defecto (fallback) para que no falle si olvidas el .env
UBER_SECRET = os.getenv("UBER_WEBHOOK_SECRET", "ChispoyNaomi@0305")


async def validar_firma_uber(
    request: Request, x_uber_signature: Optional[str] = Header(None)
):
    """
    Dependencia que intercepta la petición y valida la firma HMAC-SHA256 de Uber.
    """
    if not x_uber_signature:
        raise HTTPException(status_code=403, detail="Firma de Uber no proporcionada.")

    # Extraemos el cuerpo de la petición exactamente en bytes como llegó
    body_bytes = await request.body()

    # Calculamos la firma usando nuestra clave secreta
    firma_calculada = hmac.new(
        key=UBER_SECRET.encode("utf-8"), msg=body_bytes, digestmod=hashlib.sha256
    ).hexdigest()

    # Comparamos la firma de Uber con la nuestra de forma segura
    if not hmac.compare_digest(firma_calculada, x_uber_signature):
        raise HTTPException(
            status_code=403, detail="Firma HMAC inválida. Acceso denegado."
        )
