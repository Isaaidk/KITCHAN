import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Motor asíncrono
engine = create_async_engine(DATABASE_URL, echo=True)

# Fábrica de sesiones
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


# Dependencia para inyectar la sesión en los endpoints
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
