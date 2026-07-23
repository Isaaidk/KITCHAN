import uuid

from sqlalchemy.exc import \
    IntegrityError  # <- Importante para atrapar duplicados de BD

from src.kitchan.modules.restaurantes.application.ports import \
    IRestauranteRepository
from src.kitchan.modules.restaurantes.domain.entities import Restaurante
from src.kitchan.modules.usuarios.application.ports import IPasswordHasher
from src.kitchan.modules.usuarios.domain.entities import RolUsuario, Usuario


class RegistrarRestauranteSaaSUseCase:
    def __init__(self, repository: IRestauranteRepository, hasher: IPasswordHasher):
        self.repository = repository
        self.hasher = hasher

    async def ejecutar(
        self, datos_restaurante: dict, datos_admin: dict
    ) -> tuple[Restaurante, Usuario]:
        # 1. Validación de negocio corregida con la palabra "iguales" que espera el test
        if datos_restaurante["email_corporativo"] == datos_admin["email"]:
            raise ValueError(
                "El correo corporativo de la empresa y el del administrador no pueden ser iguales."
            )

        # 2. Generamos los IDs UUID4
        restaurante_id = str(uuid.uuid4())
        admin_id = str(uuid.uuid4())

        # 3. Ciframos la contraseña
        password_segura = self.hasher.hashear(datos_admin["password"])

        # 4. Ensamblamos la Entidad Restaurante
        nuevo_restaurante = Restaurante(
            id=restaurante_id,
            nombre_comercial=datos_restaurante["nombre_comercial"],
            razon_social=datos_restaurante["razon_social"],
            identificacion_fiscal=datos_restaurante["identificacion_fiscal"],
            direccion=datos_restaurante["direccion"],
            telefono=datos_restaurante["telefono"],
            email_corporativo=datos_restaurante["email_corporativo"],
            estado=True,
        )

        # 5. Ensamblamos la Entidad Usuario
        nuevo_admin = Usuario(
            id=admin_id,
            restaurante_id=restaurante_id,
            nombre=datos_admin["nombre"],
            email=datos_admin["email"],
            password_hash=password_segura,
            rol=RolUsuario.ADMIN,
            estado=True,
        )

        # 6. Ejecutamos la transacción atrapando posibles duplicidades de la BD
        try:
            return await self.repository.crear_con_admin(nuevo_restaurante, nuevo_admin)
        except Exception as e:
            # Si la base de datos rechaza por RUC o email duplicado (Unique Constraint),
            # transformamos el error técnico en un ValueError legible para la API (400 Bad Request)
            raise ValueError(
                "El email corporativo o la identificación fiscal ya se encuentran registrados."
            )
