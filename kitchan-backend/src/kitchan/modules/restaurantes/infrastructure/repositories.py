import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.modules.restaurantes.application.ports import IRestauranteRepository
from src.kitchan.modules.restaurantes.domain.entities import Restaurante
from src.kitchan.modules.restaurantes.domain.exceptions import RegistroDuplicadoError
from src.kitchan.modules.restaurantes.infrastructure.models import RestauranteModel
from src.kitchan.modules.usuarios.domain.entities import Usuario
from src.kitchan.modules.usuarios.infrastructure.models import UsuarioModel


def _mensaje_duplicado(mensaje_error: str) -> str:
    """Mensaje claro para el cliente según el constraint que falló. Contempla
    los nombres de Postgres (ej. usuarios_email_key) y de SQLite (ej.
    usuarios.email), que es la base que usan los tests.

    Para el restaurante se da un mensaje conjunto: la base reporta solo el
    primer constraint que falla, y el RUC y el email corporativo pueden estar
    repetidos a la vez."""
    if any(
        clave in mensaje_error
        for clave in ("usuarios_email_key", "ix_usuarios_email", "usuarios.email")
    ):
        return "El email del administrador ya está registrado en el sistema."
    return (
        "El email corporativo o la identificación fiscal ya se encuentran registrados."
    )


class PostgresRestauranteRepository(IRestauranteRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def crear_con_admin(
        self, restaurante: Restaurante, admin: Usuario
    ) -> tuple[Restaurante, Usuario]:
        # 1. Mapeamos la Entidad de Dominio Restaurante al Modelo de SQLAlchemy
        restaurante_model = RestauranteModel(
            id=uuid.UUID(restaurante.id),
            nombre_comercial=restaurante.nombre_comercial,
            razon_social=restaurante.razon_social,
            identificacion_fiscal=restaurante.identificacion_fiscal,
            direccion=restaurante.direccion,
            telefono=restaurante.telefono,
            email_corporativo=restaurante.email_corporativo,
            estado=restaurante.estado,
        )

        # 2. Mapeamos la Entidad de Dominio Usuario al Modelo de SQLAlchemy
        admin_model = UsuarioModel(
            id=uuid.UUID(admin.id),
            restaurante_id=uuid.UUID(admin.restaurante_id),
            nombre=admin.nombre,
            email=admin.email,
            password_hash=admin.password_hash,
            rol=admin.rol.value,  # Extraemos el string del Enum
            estado=admin.estado,
        )

        try:
            # 3. Preparamos ambas inserciones en la misma sesión
            self.session.add(restaurante_model)
            self.session.add(admin_model)

            # 4. Ejecutamos la Transacción ACID (O se guardan los dos, o ninguno)
            await self.session.commit()

            return restaurante, admin

        except IntegrityError as e:
            # Si falla la transacción (ej. violación de constraint de unicidad),
            # hacemos rollback y traducimos el error técnico a uno de dominio.
            await self.session.rollback()
            raise RegistroDuplicadoError(_mensaje_duplicado(str(e.orig))) from e

        except Exception as e:
            # Para cualquier otro error inesperado (ej. pérdida de conexión), también revertimos
            await self.session.rollback()
            raise e
