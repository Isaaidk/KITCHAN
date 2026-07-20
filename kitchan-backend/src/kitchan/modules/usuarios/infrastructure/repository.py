# Adaptador DE SALIDA
# inserta los datos en la BD y devuelve el usuario creado
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Importamos los puertos y entidades (El Núcleo)
from src.kitchan.modules.usuarios.application.ports import IUsuarioRepository
from src.kitchan.modules.usuarios.domain.entities import Usuario

# Importamos el modelo físico de la base de datos (La Infraestructura)
from src.kitchan.modules.usuarios.infrastructure.models import UsuarioModel
from sqlalchemy import select
from src.kitchan.modules.usuarios.application.ports import IUsuarioRepository
from src.kitchan.modules.usuarios.domain.entities import Usuario
from src.kitchan.modules.usuarios.infrastructure.models import UsuarioModel


class PostgresUsuarioRepository(IUsuarioRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def guardar(self, usuario: Usuario) -> Usuario:
        nuevo_modelo = UsuarioModel(
            id=usuario.id,
            nombre=usuario.nombre,
            email=usuario.email,
            password_hash=usuario.password_hash,
            rol=usuario.rol.value,
            estado=usuario.estado,
        )

        # Agregacion del usuario a postgre
        self.session.add(nuevo_modelo)
        await self.session.commit()
        await self.session.refresh(nuevo_modelo)

        # 3. Devolver la entidad de Dominio pura (el núcleo no debe tocar SQLAlchemy)
        return nuevo_modelo.to_domain()

    async def buscar_por_email(self, email: str) -> Optional[Usuario]:
        # 1. Consulta optimizada y asíncrona
        stmt = select(UsuarioModel).where(UsuarioModel.email == email)
        resultado = await self.session.execute(stmt)

        # 2. Extraer el primer resultado o None
        modelo = resultado.scalar_one_or_none()

        if modelo is None:
            return None

        # 3. Retornar la entidad de Dominio pura
        return modelo.to_domain()
