import bcrypt
from src.kitchan.modules.usuarios.application.ports import IPasswordHasher


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
