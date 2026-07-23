import sqlite3
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import CHAR, TypeDecorator

# Importa la Base de datos y tus modelos de infraestructura
from src.kitchan.core.database import Base, get_db
from src.kitchan.main import app
from src.kitchan.modules.restaurantes.infrastructure.models import RestauranteModel
from src.kitchan.modules.usuarios.infrastructure.models import UsuarioModel


# --- ADAPTADOR SEGURO DE UUID PARA SQLITE ---
class SQLiteUUIDSafe(TypeDecorator):
    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return str(value)


@compiles(PG_UUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "VARCHAR(36)"


# Interceptamos el tipo a nivel de compilación de esquema para SQLite
@compiles(PG_UUID, "sqlite")
def compile_pg_uuid_as_char(element, compiler, **kw):
    return "VARCHAR(36)"


# ----------------------------------------------------

# Base de datos SQLite en memoria asíncrona para pruebas rápidas y aisladas
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
