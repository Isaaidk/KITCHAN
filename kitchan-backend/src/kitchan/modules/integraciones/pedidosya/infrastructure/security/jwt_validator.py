"""Infraestructura de PedidosYa: validación del JWT Bearer que Delivery Hero
envía en cada llamada a nuestro endpoint de dispatch.

A diferencia de Uber (firma HMAC-SHA256 sobre el body crudo, ver
integraciones/uber/infrastructure/security/hmac_validator.py), PedidosYa
firma un JWT (HS512) con un secreto compartido y lo manda en el header
`Authorization: Bearer <jwt>` — es un mecanismo de verificación distinto, no
una variante del validador de Uber, aunque cumple el mismo rol arquitectónico
(autenticar al emisor del pedido entrante) con el mismo estilo de
implementación (función pura + dependencia de FastAPI).
"""

import os
from typing import Optional

from fastapi import Header, HTTPException
from jose import JWTError, jwt

PEDIDOSYA_JWT_ALGORITHM = "HS512"
PEDIDOSYA_REQUIRED_CLAIM = "service"
PEDIDOSYA_REQUIRED_VALUE = "middleware"


def verify_pedidosya_jwt(token: str, shared_secret: str) -> dict:
    """Verifica la firma del JWT y el claim `service: middleware` que
    documenta PedidosYa. Lanza JWTError/ValueError si algo no coincide."""
    payload = jwt.decode(token, shared_secret, algorithms=[PEDIDOSYA_JWT_ALGORITHM])

    if payload.get(PEDIDOSYA_REQUIRED_CLAIM) != PEDIDOSYA_REQUIRED_VALUE:
        raise ValueError(
            f"Claim '{PEDIDOSYA_REQUIRED_CLAIM}' inválido en el token de PedidosYa."
        )

    return payload


async def validar_jwt_pedidosya(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Dependencia de FastAPI: exige `Authorization: Bearer <jwt>` firmado
    con el secreto compartido de PedidosYa (PEDIDOSYA_JWT_SECRET, distinto en
    staging/producción según la documentación)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Token Bearer de PedidosYa faltante."
        )

    shared_secret = os.getenv("PEDIDOSYA_JWT_SECRET")
    if not shared_secret:
        raise HTTPException(
            status_code=500, detail="Falta configurar PEDIDOSYA_JWT_SECRET"
        )

    token = authorization[len("Bearer ") :].strip()

    try:
        return verify_pedidosya_jwt(token, shared_secret)
    except (JWTError, ValueError) as error:
        print(f"🚨 ALERTA: JWT de PedidosYa inválido: {error}")
        raise HTTPException(status_code=401, detail="Token de PedidosYa inválido.")
