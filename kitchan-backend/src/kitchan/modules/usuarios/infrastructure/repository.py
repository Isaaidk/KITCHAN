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

    async def buscar_por_id(self, id: str) -> Optional[Usuario]:
        stmt = select(UsuarioModel).where(UsuarioModel.id == id)
        resultado = await self.session.execute(stmt)

        modelo = resultado.scalar_one_or_none()

        if modelo is None:
            return None

        return modelo.to_domain()

    async def eliminar(self, id: str) -> None:
        stmt = select(UsuarioModel).where(UsuarioModel.id == id)
        resultado = await self.session.execute(stmt)

        modelo = resultado.scalar_one_or_none()

        if modelo is not None:
            await self.session.delete(modelo)
            await self.session.commit()

    async def editar_contraseña(
        self, email: str, password_hash: str
    ) -> Optional[Usuario]:
        stmt = select(UsuarioModel).where(UsuarioModel.email == email)
        resultado = await self.session.execute(stmt)

        modelo = resultado.scalar_one_or_none()

        if modelo is None:
            return None

        modelo.password_hash = password_hash

        await self.session.commit()
        await self.session.refresh(modelo)

        return modelo.to_domain()

    async def listar(self) -> list[Usuario]:
        stmt = select(UsuarioModel)
        resultado = await self.session.execute(stmt)

        modelos = resultado.scalars().all()

        return [modelo.to_domain() for modelo in modelos]
