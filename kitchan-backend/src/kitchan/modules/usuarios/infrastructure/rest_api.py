# Adaptador de entrada
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

# Importamos la conexión a BD y el núcleo
from src.kitchan.core.database import get_db
from src.kitchan.modules.usuarios.application.use_cases import (
    CrearUsuarioPorAdminUseCase,
    EditarUsuarioUCase,
    EliminarUsuarioUseCase,
    ListarUsuariosPorRestauranteUCase,
    ListarUsuariosUCase,
    LoginUsuarioUseCase,
)
from src.kitchan.modules.usuarios.domain.entities import RolUsuario
from src.kitchan.modules.usuarios.infrastructure.auth_dependencies import (
    obtener_usuario_actual,
    requiere_rol,
)
from src.kitchan.modules.usuarios.infrastructure.repository import (
    PostgresUsuarioRepository,
)
from src.kitchan.modules.usuarios.infrastructure.security import (
    BcryptPasswordHasher,
    JWTTokenGenerator,
)

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios"])


# --- ESQUEMAS PYDANTIC (Data Transfer Objects) ---
class CrearUsuarioAdminRequest(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: RolUsuario


class EditarUsuarioRequest(BaseModel):
    password_hash: str


class UsuarioResponse(BaseModel):
    id: str
    restaurante_id: str
    nombre: str
    email: str
    rol: str
    estado: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


# -------------------------------------------------
# Creación de ruta para que un Administrador cree un usuario
# Protegida: solo un token con rol ADMIN puede ejecutar esta acción
#
@router.post(
    "/restaurante/{restaurante_id}",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_usuario_por_admin(
    restaurante_id: str,
    request: CrearUsuarioAdminRequest,
    db: AsyncSession = Depends(get_db),
    usuario_actual: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
):
    repo = PostgresUsuarioRepository(session=db)
    hasher_real = BcryptPasswordHasher()
    caso_uso = CrearUsuarioPorAdminUseCase(repository=repo, hasher=hasher_real)

    try:
        usuario = await caso_uso.ejecutar(
            restaurante_id=restaurante_id,
            admin_rol=usuario_actual["rol"],
            datos_nuevo_usuario=request.model_dump(),
        )

        return UsuarioResponse(
            id=str(usuario.id),
            restaurante_id=str(usuario.restaurante_id),
            nombre=usuario.nombre,
            email=usuario.email,
            rol=usuario.rol.value,
            estado=usuario.estado,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------
# Creación de ruta para la eliminación de usuarios
# Protegida: solo un token con rol ADMIN puede ejecutar esta acción
#
@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(
    usuario_id: str,
    db: AsyncSession = Depends(get_db),
    usuario_actual: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
):
    repo = PostgresUsuarioRepository(session=db)
    caso_uso = EliminarUsuarioUseCase(repository=repo)

    try:
        await caso_uso.ejecutar(usuario_id=usuario_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Protegida: cualquier usuario autenticado puede ejecutarla, pero solo sobre su
# propia cuenta (el email del token debe coincidir con el email de la ruta)
@router.patch("/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def editar_contraseña(
    email: str,
    data: EditarUsuarioRequest,
    db: AsyncSession = Depends(get_db),
    usuario_actual: dict = Depends(obtener_usuario_actual),
):
    if usuario_actual["sub"] != email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes editar la contraseña de otro usuario",
        )

    hasher_real = BcryptPasswordHasher()
    repo = PostgresUsuarioRepository(session=db)
    caso_uso = EditarUsuarioUCase(repository=repo, hasher=hasher_real)

    try:
        await caso_uso.ejecutar(email=email, password_hash=data.password_hash)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Protegida: solo un token con rol ADMIN puede listar los usuarios de un restaurante
@router.get(
    "/restaurante/{restaurante_id}",
    response_model=list[UsuarioResponse],
    status_code=status.HTTP_200_OK,
)
async def listar_usuarios_por_restaurante(
    restaurante_id: str,
    db: AsyncSession = Depends(get_db),
    usuario_actual: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
):
    repo = PostgresUsuarioRepository(session=db)
    caso_uso = ListarUsuariosPorRestauranteUCase(repository=repo)

    usuarios = await caso_uso.ejecutar(restaurante_id)

    return [
        UsuarioResponse(
            id=str(u.id),
            restaurante_id=str(u.restaurante_id),
            nombre=u.nombre,
            email=u.email,
            rol=u.rol.value,
            estado=u.estado,
        )
        for u in usuarios
    ]


# Protegida: solo un token con rol ADMIN puede listar todos los usuarios
@router.get("/", response_model=list[UsuarioResponse], status_code=status.HTTP_200_OK)
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    usuario_actual: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
):
    repo = PostgresUsuarioRepository(session=db)
    caso_uso = ListarUsuariosUCase(repository=repo)

    usuarios = await caso_uso.ejecutar()

    return [
        UsuarioResponse(
            id=str(u.id),
            restaurante_id=str(u.restaurante_id),
            nombre=u.nombre,
            email=u.email,
            rol=u.rol.value,
            estado=u.estado,
        )
        for u in usuarios
    ]


# -------------------------------------------------
# Creación de ruta para el login de usuarios
#
@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login_usuario(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = PostgresUsuarioRepository(session=db)
    hasher_real = BcryptPasswordHasher()
    token_generator_real = JWTTokenGenerator()

    caso_uso = LoginUsuarioUseCase(
        repository=repo, hasher=hasher_real, token_generator=token_generator_real
    )

    try:
        usuario, token = await caso_uso.ejecutar(
            email=request.email, password=request.password
        )

        return LoginResponse(
            access_token=token,
            usuario=UsuarioResponse(
                id=str(usuario.id),
                restaurante_id=str(usuario.restaurante_id),
                nombre=usuario.nombre,
                email=usuario.email,
                rol=usuario.rol.value,
                estado=usuario.estado,
            ),
        )
    except ValueError as e:
        detail = str(e)
        if detail == "Rol de usuario no reconocido":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
