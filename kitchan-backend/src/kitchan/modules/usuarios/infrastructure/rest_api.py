# Aadaptador de entrada
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

# Importamos la conexión a BD y el núcleo
from src.kitchan.core.database import get_db
from src.kitchan.modules.usuarios.domain.entities import RolUsuario
from src.kitchan.modules.usuarios.application.use_cases import (
    CrearUsuarioUseCase,
    EliminarUsuarioUseCase,
)
from src.kitchan.modules.usuarios.infrastructure.repository import (
    PostgresUsuarioRepository,
)

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios"])


# --- ESQUEMAS PYDANTIC (Data Transfer Objects) ---
class CrearUsuarioRequest(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: RolUsuario


class UsuarioResponse(BaseModel):
    id: str
    nombre: str
    email: str
    rol: str
    estado: bool


# -------------------------------------------------
# Creacion de ruta para la creacion de usuarios
#
@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    request: CrearUsuarioRequest, db: AsyncSession = Depends(get_db)
):
    # 1. Instanciamos el Adaptador de Salida (Repositorio)
    repo = PostgresUsuarioRepository(session=db)

    # 2. Inyectamos el repositorio al Caso de Uso
    caso_uso = CrearUsuarioUseCase(repository=repo)

    # 3. Ejecutamos el núcleo y capturamos errores de negocio
    try:
        # IMPORTANTE: Aquí la contraseña debería encriptarse con Bcrypt antes de guardarla.
        # Por ahora la pasamos directo para probar la arquitectura.
        usuario = await caso_uso.ejecutar(
            nombre=request.nombre,
            email=request.email,
            password_hash=request.password,
            rol=request.rol,
        )

        # 4. Retornamos la respuesta mapeada
        return UsuarioResponse(
            id=usuario.id,
            nombre=usuario.nombre,
            email=usuario.email,
            rol=usuario.rol.value,
            estado=usuario.estado,
        )
    except ValueError as e:  # Capturamos el error de "Email ya registrado"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------
# Creacion de ruta para la eliminacion de usuarios
#
@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(usuario_id: str, db: AsyncSession = Depends(get_db)):
    # 1. Instanciamos el Adaptador de Salida (Repositorio)
    repo = PostgresUsuarioRepository(session=db)

    # 2. Inyectamos el repositorio al Caso de Uso
    caso_uso = EliminarUsuarioUseCase(repository=repo)

    # 3. Ejecutamos el núcleo y capturamos errores de negocio
    try:
        await caso_uso.ejecutar(usuario_id=usuario_id)
    except ValueError as e:  # Capturamos el error de "Usuario no encontrado"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
