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


def _secreto_restablecimiento() -> str:
    # Clave derivada: un token de restablecimiento nunca vale como token de sesión.
    return f"{os.getenv('SECRET_KEY')}:restablecer-password"


def crear_token_restablecimiento(data: dict, minutos: int) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    return jwt.encode(
        payload, _secreto_restablecimiento(), algorithm=os.getenv("ALGORITHM", "HS256")
    )


def decodificar_token_restablecimiento(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _secreto_restablecimiento(),
            algorithms=[os.getenv("ALGORITHM", "HS256")],
        )
    except JWTError:
        raise ValueError("El enlace de restablecimiento no es válido o ya venció")


def decodificar_access_token(token: str) -> dict:
    secret_key = os.getenv("SECRET_KEY")
    algorithm = os.getenv("ALGORITHM", "HS256")

    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError:
        raise ValueError("Token inválido o expirado")
