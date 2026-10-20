import bcrypt

from src.kitchan.core.security import crear_access_token, decodificar_access_token
from src.kitchan.modules.usuarios.application.ports import (
    IPasswordHasher,
    ITokenGenerator,
)


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


# Adaptador de salida: envuelve el shared kernel de JWT (src.kitchan.core.security)
# para cumplir el puerto ITokenGenerator del módulo usuarios.
class JWTTokenGenerator(ITokenGenerator):
    def generar_token(self, data: dict) -> str:
        return crear_access_token(data)

    def decodificar_token(self, token: str) -> dict:
        return decodificar_access_token(token)
