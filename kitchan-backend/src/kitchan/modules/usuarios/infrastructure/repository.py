# Adaptador DE SALIDA
# Inserta los datos en la BD y devuelve el usuario creado
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Importamos los puertos y entidades (El Núcleo)
from src.kitchan.modules.usuarios.application.ports import (
    ICodigosRecuperacionRepository,
    IUsuarioRepository,
)
from src.kitchan.modules.usuarios.domain.entities import CodigoRecuperacion, Usuario
from src.kitchan.modules.usuarios.infrastructure.models import (
    CodigoRecuperacionModel,
    UsuarioModel,
)


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

    async def actualizar_datos(
        self, usuario_id: str, nombre: str, rol
    ) -> Optional[Usuario]:
        stmt = select(UsuarioModel).where(UsuarioModel.id == uuid.UUID(str(usuario_id)))
        resultado = await self.session.execute(stmt)
        modelo = resultado.scalar_one_or_none()

        if modelo is None:
            return None

        modelo.nombre = nombre
        modelo.rol = rol.value

        await self.session.commit()
        await self.session.refresh(modelo)

        return modelo.to_domain()

    async def cambiar_estado(self, usuario_id: str, estado: bool) -> Optional[Usuario]:
        stmt = select(UsuarioModel).where(UsuarioModel.id == uuid.UUID(str(usuario_id)))
        resultado = await self.session.execute(stmt)
        modelo = resultado.scalar_one_or_none()

        if modelo is None:
            return None

        modelo.estado = estado

        await self.session.commit()
        await self.session.refresh(modelo)

        return modelo.to_domain()

    async def registrar_acceso(self, usuario_id: str) -> None:
        await self.session.execute(
            update(UsuarioModel)
            .where(UsuarioModel.id == uuid.UUID(str(usuario_id)))
            .values(ultimo_acceso=datetime.now(timezone.utc))
        )
        await self.session.commit()

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


class PostgresCodigosRecuperacionRepository(ICodigosRecuperacionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def crear(self, codigo: CodigoRecuperacion) -> CodigoRecuperacion:
        modelo = CodigoRecuperacionModel(
            id=uuid.UUID(str(codigo.id)),
            usuario_id=uuid.UUID(str(codigo.usuario_id)),
            codigo_hash=codigo.codigo_hash,
            expira_en=codigo.expira_en,
            intentos=codigo.intentos,
            usado=codigo.usado,
            creado_en=codigo.creado_en,
        )
        self.session.add(modelo)
        await self.session.commit()
        await self.session.refresh(modelo)
        return modelo.to_domain()

    async def buscar_por_id(self, codigo_id: str) -> Optional[CodigoRecuperacion]:
        try:
            id_codigo = uuid.UUID(str(codigo_id))
        except ValueError:
            return None
        resultado = await self.session.execute(
            select(CodigoRecuperacionModel).where(
                CodigoRecuperacionModel.id == id_codigo
            )
        )
        modelo = resultado.scalar_one_or_none()
        return modelo.to_domain() if modelo else None

    async def ultimo_de_usuario(self, usuario_id: str) -> Optional[CodigoRecuperacion]:
        resultado = await self.session.execute(
            select(CodigoRecuperacionModel)
            .where(CodigoRecuperacionModel.usuario_id == uuid.UUID(str(usuario_id)))
            .order_by(CodigoRecuperacionModel.creado_en.desc())
            .limit(1)
        )
        modelo = resultado.scalar_one_or_none()
        return modelo.to_domain() if modelo else None

    async def registrar_intento_fallido(self, codigo_id: str) -> None:
        await self.session.execute(
            update(CodigoRecuperacionModel)
            .where(CodigoRecuperacionModel.id == uuid.UUID(str(codigo_id)))
            .values(intentos=CodigoRecuperacionModel.intentos + 1)
        )
        await self.session.commit()

    async def marcar_usado(self, codigo_id: str) -> None:
        await self.session.execute(
            update(CodigoRecuperacionModel)
            .where(CodigoRecuperacionModel.id == uuid.UUID(str(codigo_id)))
            .values(usado=True)
        )
        await self.session.commit()

    async def invalidar_de_usuario(self, usuario_id: str) -> None:
        await self.session.execute(
            update(CodigoRecuperacionModel)
            .where(
                CodigoRecuperacionModel.usuario_id == uuid.UUID(str(usuario_id)),
                CodigoRecuperacionModel.usado.is_(False),
            )
            .values(usado=True)
        )
        await self.session.commit()
