# Adaptador DE SALIDA
# Inserta los datos en la BD y devuelve el usuario creado
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
# Importamos los puertos y entidades (El Núcleo)
from src.kitchan.modules.usuarios.application.ports import IUsuarioRepository
from src.kitchan.modules.usuarios.domain.entities import Usuario
from src.kitchan.modules.usuarios.infrastructure.models import UsuarioModel


class PostgresUsuarioRepository(IUsuarioRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def crear(self, usuario: Usuario) -> Usuario:
        # CORREGIDO: Usamos la variable 'usuario' de la firma
        nuevo_modelo = UsuarioModel(
            id=uuid.UUID(str(usuario.id)),
            restaurante_id=uuid.UUID(
                str(usuario.restaurante_id)
            ),  # <- Clave para el aislamiento multi-tenant
            nombre=usuario.nombre,
            email=usuario.email,
            password_hash=usuario.password_hash,
            rol=usuario.rol.value,
            estado=usuario.estado,
        )

        # Agregación del usuario a Postgres
        self.session.add(nuevo_modelo)
        await self.session.commit()
        await self.session.refresh(nuevo_modelo)

        # Devolver la entidad de Dominio pura
        return nuevo_modelo.to_domain()

    async def buscar_por_email(self, email: str) -> Optional[Usuario]:
        stmt = select(UsuarioModel).where(UsuarioModel.email == email)
        resultado = await self.session.execute(stmt)
        modelo = resultado.scalar_one_or_none()

        if modelo is None:
            return None

        return modelo.to_domain()

    async def buscar_por_id(self, id: str) -> Optional[Usuario]:
        # Convertimos a uuid.UUID para evitar problemas de tipos en la consulta
        uuid_val = uuid.UUID(str(id)) if not isinstance(id, uuid.UUID) else id
        stmt = select(UsuarioModel).where(UsuarioModel.id == uuid_val)
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

    async def listar_por_restaurante(self, restaurante_id: str) -> list[Usuario]:
        uuid_val = (
            uuid.UUID(str(restaurante_id))
            if not isinstance(restaurante_id, uuid.UUID)
            else restaurante_id
        )
        # Consulta estrictamente filtrada por el ID del restaurante
        stmt = select(UsuarioModel).where(UsuarioModel.restaurante_id == uuid_val)
        resultado = await self.session.execute(stmt)
        modelos = resultado.scalars().all()

        return [modelo.to_domain() for modelo in modelos]

    async def listar(self) -> list[Usuario]:
        stmt = select(UsuarioModel)
        resultado = await self.session.execute(stmt)
        modelos = resultado.scalars().all()

        return [modelo.to_domain() for modelo in modelos]
