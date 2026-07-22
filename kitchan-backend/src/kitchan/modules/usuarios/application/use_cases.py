# CASO DE USO
# Define que los datos cumplan con el caso de uso, en este caso debe de revisar primero que el email no este creado
# y si no lo esta pide que se almacene el usuario y tma todos los datos
from src.kitchan.modules.usuarios.domain.entities import Usuario, RolUsuario
from src.kitchan.modules.usuarios.application.ports import (
    IUsuarioRepository,
    IPasswordHasher,
    ITokenGenerator,
)

import uuid


class CrearUsuarioUseCase:
    def __init__(self, repository: IUsuarioRepository, hasher: IPasswordHasher):
        self.repository = repository
        self.hasher = hasher

    async def ejecutar(
        self, nombre: str, email: str, password_hash: str, rol: RolUsuario
    ) -> Usuario:
        # Validar si el usuario existe
        usuario_existente = await self.repository.buscar_por_email(email)
        if usuario_existente:
            raise ValueError("El email ya fue registrado")

        password_segura = self.hasher.hashear(password_hash)

        # Creacion de un Usuario con los datos correctos
        nuevoUsuario = Usuario(
            id=str(uuid.uuid4()),
            nombre=nombre,  # Pasamos la variable local
            email=email,  # Pasamos la variable local
            password_hash=password_segura,  # Pasamos la variable local
            rol=rol,  # Pasamos la variable local
            estado=True,  # Asignación directa del valor por defecto
        )

        return await self.repository.guardar(nuevoUsuario)


class EliminarUsuarioUseCase:
    def __init__(self, repository: IUsuarioRepository):
        self.repository = repository

    async def ejecutar(self, usuario_id: str) -> None:
        # Validar que el usuario exista antes de eliminar
        usuario_existente = await self.repository.buscar_por_id(usuario_id)
        if usuario_existente is None:
            raise ValueError("Usuario no encontrado")

        await self.repository.eliminar(usuario_id)


class EditarUsuarioUCase:
    def __init__(self, repository: IUsuarioRepository, hasher: IPasswordHasher):
        self.repository = repository
        self.hasher = hasher

    async def ejecutar(self, email: str, password_hash: str) -> None:
        # Editar contraseña de usuario
        usuario_exisente = await self.repository.buscar_por_email(email)
        if usuario_exisente is None:
            raise ValueError("El usuario no existe")
        password_segura = self.hasher.hashear(password_hash)
        await self.repository.editar_contraseña(email, password_segura)


class ListarUsuariosUCase:
    def __init__(self, repository: IUsuarioRepository):
        self.repository = repository

    async def ejecutar(self):
        return await self.repository.listar()


class LoginUsuarioUseCase:
    def __init__(
        self,
        repository: IUsuarioRepository,
        hasher: IPasswordHasher,
        token_generator: ITokenGenerator,
    ):
        self.repository = repository
        self.hasher = hasher
        self.token_generator = token_generator

    async def ejecutar(self, email: str, password: str) -> tuple[Usuario, str]:
        usuario = await self.repository.buscar_por_email(email)

        # Mismo mensaje genérico si el usuario no existe o si la contraseña
        # no coincide, para no revelar si un email está registrado
        if usuario is None or not self.hasher.verificar(
            password, usuario.password_hash
        ):
            raise ValueError("Credenciales inválidas")

        if not isinstance(usuario.rol, RolUsuario):
            raise ValueError("Rol de usuario no reconocido")

        token = self.token_generator.generar_token(
            {"sub": usuario.email, "id": usuario.id, "rol": usuario.rol.value}
        )

        return usuario, token
