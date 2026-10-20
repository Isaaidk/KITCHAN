# CASO DE USO
# Define que los datos cumplan con el caso de uso, en este caso debe de revisar primero que el email no este creado
# y si no lo esta pide que se almacene el usuario y tma todos los datos
import uuid

from src.kitchan.modules.usuarios.application.ports import (
    IPasswordHasher,
    ITokenGenerator,
    IUsuarioRepository,
)
from src.kitchan.modules.usuarios.domain.entities import RolUsuario, Usuario


class ListarUsuariosPorRestauranteUCase:
    """Listar usuarios filtrados estrictamente por el restaurante del admin."""

    def __init__(self, repository: IUsuarioRepository):
        self.repository = repository

    async def ejecutar(self, restaurante_id: str):
        # Aquí aseguras el aislamiento multi-tenant en la consulta
        return await self.repository.listar_por_restaurante(restaurante_id)


class EliminarUsuarioUseCase:
    def __init__(self, repository: IUsuarioRepository):
        self.repository = repository

    async def ejecutar(self, usuario_id: str, admin_restaurante_id: str) -> None:
        # Validar que el usuario exista antes de eliminar
        usuario_existente = await self.repository.buscar_por_id(usuario_id)
        if usuario_existente is None:
            raise ValueError("Usuario no encontrado")

        # Aislamiento multi-tenant: un admin solo puede eliminar usuarios de
        # su propio restaurante.
        if str(usuario_existente.restaurante_id) != str(admin_restaurante_id):
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


class EditarUsuarioPorAdminUseCase:
    """A diferencia de EditarUsuarioUCase (solo contraseña, solo la propia
    cuenta), permite a un Admin editar nombre/rol de cualquier usuario de su
    restaurante."""

    def __init__(self, repository: IUsuarioRepository):
        self.repository = repository

    async def ejecutar(
        self, usuario_id: str, nombre: str, rol: str, admin_restaurante_id: str
    ) -> Usuario:
        usuario_existente = await self.repository.buscar_por_id(usuario_id)
        if usuario_existente is None:
            raise ValueError("Usuario no encontrado")

        # Aislamiento multi-tenant: un admin solo puede editar usuarios de
        # su propio restaurante.
        if str(usuario_existente.restaurante_id) != str(admin_restaurante_id):
            raise ValueError("Usuario no encontrado")

        if rol not in [RolUsuario.ADMIN.value, RolUsuario.OPERADOR.value]:
            raise ValueError("Rol no válido para asignar.")

        actualizado = await self.repository.actualizar_datos(
            usuario_id, nombre, RolUsuario(rol)
        )
        return actualizado


class CambiarEstadoUsuarioUseCase:
    def __init__(self, repository: IUsuarioRepository):
        self.repository = repository

    async def ejecutar(
        self, usuario_id: str, estado: bool, admin_restaurante_id: str
    ) -> Usuario:
        usuario_existente = await self.repository.buscar_por_id(usuario_id)
        if usuario_existente is None:
            raise ValueError("Usuario no encontrado")

        # Aislamiento multi-tenant: un admin solo puede activar/desactivar
        # usuarios de su propio restaurante.
        if str(usuario_existente.restaurante_id) != str(admin_restaurante_id):
            raise ValueError("Usuario no encontrado")

        actualizado = await self.repository.cambiar_estado(usuario_id, estado)
        return actualizado


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

        if usuario is None or not self.hasher.verificar(
            password, usuario.password_hash
        ):
            raise ValueError("Credenciales inválidas")

        if not isinstance(usuario.rol, RolUsuario):
            raise ValueError("Rol de usuario no reconocido")

        # Generamos el token incluyendo el restaurante_id para las futuras peticiones
        token = self.token_generator.generar_token(
            {
                "sub": usuario.email,
                "id": usuario.id,
                "rol": usuario.rol.value,
                "restaurante_id": usuario.restaurante_id,  # <- Clave para la seguridad multi-tenant
            }
        )

        return usuario, token


class CrearUsuarioPorAdminUseCase:
    def __init__(self, repository: IUsuarioRepository, hasher: IPasswordHasher):
        self.repository = repository
        self.hasher = hasher

    async def ejecutar(
        self, restaurante_id: str, admin_rol: str, datos_nuevo_usuario: dict
    ) -> Usuario:
        # 1. Regla de negocio: Un OPERADOR no puede crear usuarios
        if admin_rol != RolUsuario.ADMIN.value:
            raise ValueError(
                "Acceso denegado: Los operadores no tienen permisos para crear usuarios."
            )

        # 2. VALIDAR ROL SOLICITUD (¡MOVIMOS ESTO ANTES DEL EMAIL PARA QUE EL TEST DE ROL NO VALIDE DUPLICIDAD PRIMERO!)
        rol_solicitado = datos_nuevo_usuario.get("rol", "OPERADOR")
        # Si el rol viene como Enum de Pydantic, extraemos su valor de forma segura
        if hasattr(rol_solicitado, "value"):
            rol_solicitado = rol_solicitado.value

        if rol_solicitado not in [RolUsuario.ADMIN.value, RolUsuario.OPERADOR.value]:
            raise ValueError("Rol no válido para asignar.")

        # 3. Validar si el correo ya está registrado globalmente
        usuario_existente = await self.repository.buscar_por_email(
            datos_nuevo_usuario["email"]
        )
        if usuario_existente:
            raise ValueError("El correo electrónico ya se encuentra registrado.")

        # 4. Cifrar contraseña y crear entidad
        password_segura = self.hasher.hashear(datos_nuevo_usuario["password"])
        nuevo_usuario = Usuario(
            id=str(uuid.uuid4()),
            restaurante_id=restaurante_id,
            nombre=datos_nuevo_usuario["nombre"],
            email=datos_nuevo_usuario["email"],
            password_hash=password_segura,
            rol=RolUsuario(rol_solicitado),
            estado=True,
        )

        return await self.repository.crear(nuevo_usuario)
