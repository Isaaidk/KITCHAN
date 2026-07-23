import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.modules.restaurantes.application.ports import \
    IRestauranteRepository
from src.kitchan.modules.restaurantes.domain.entities import Restaurante
from src.kitchan.modules.restaurantes.infrastructure.models import \
    RestauranteModel
from src.kitchan.modules.usuarios.domain.entities import Usuario
from src.kitchan.modules.usuarios.infrastructure.models import UsuarioModel


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
            # Si falla la transacción (ej. violación de constraint de unicidad), hacemos rollback
            await self.session.rollback()

            mensaje_error = str(e.orig)
            # Evaluamos el error específico para darle un mensaje claro al cliente
            if (
                "usuarios_email_key" in mensaje_error
                or "ix_usuarios_email" in mensaje_error
            ):
                raise ValueError(
                    "El email del administrador ya está registrado en el sistema."
                )
            elif "identificacion_fiscal" in mensaje_error:
                raise ValueError(
                    "La identificación fiscal (RUC/NIT) ya está registrada para otro restaurante."
                )
            else:
                raise ValueError(
                    "Error de integridad de datos al intentar registrar el restaurante."
                )

        except Exception as e:
            # Para cualquier otro error inesperado (ej. pérdida de conexión), también revertimos
            await self.session.rollback()
            raise e
