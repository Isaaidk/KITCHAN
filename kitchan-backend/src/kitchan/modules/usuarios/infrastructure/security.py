import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from src.kitchan.modules.usuarios.application.ports import (IPasswordHasher,
                                                            ITokenGenerator)


# importacio de byscript para el uso del hasheo
class BcryptPasswordHasher(IPasswordHasher):
    def hashear(self, password: str) -> str:
        # bcrypt necesita trabajar con bytes
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
        # Devolvemos el string decodificado para guardarlo en la BD
        return hashed_bytes.decode("utf-8")

    def verificar(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )


# Adaptador de salida: genera tokens de acceso JWT firmados con la SECRET_KEY
# configurada en el .env, usando python-jose
class JWTTokenGenerator(ITokenGenerator):
    def generar_token(self, data: dict) -> str:
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM", "HS256")
        expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

        payload = data.copy()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)

        return jwt.encode(payload, secret_key, algorithm=algorithm)
