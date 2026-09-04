import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

# Shared kernel: emisión/verificación de JWT reutilizada por cualquier módulo
# (usuarios la envuelve en su puerto ITokenGenerator; el handshake WS de
# pedidos la usa directo, sin depender de internals de usuarios).


def crear_access_token(data: dict) -> str:
    secret_key = os.getenv("SECRET_KEY")
    algorithm = os.getenv("ALGORITHM", "HS256")
    expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)

    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decodificar_access_token(token: str) -> dict:
    secret_key = os.getenv("SECRET_KEY")
    algorithm = os.getenv("ALGORITHM", "HS256")

    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError:
        raise ValueError("Token inválido o expirado")
