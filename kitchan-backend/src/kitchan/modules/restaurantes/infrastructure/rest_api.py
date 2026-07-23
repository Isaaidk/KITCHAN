from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
# Dependencias de tu proyecto (ajusta las rutas según tu estructura)
from src.kitchan.core.database import get_db
from src.kitchan.modules.restaurantes.application.use_cases import \
    RegistrarRestauranteSaaSUseCase
from src.kitchan.modules.restaurantes.infrastructure.repositories import \
    PostgresRestauranteRepository
from src.kitchan.modules.restaurantes.infrastructure.schemas import (
    OnboardingRequest, OnboardingResponse, RestauranteResponse,
    UsuarioSaaSResponse)
from src.kitchan.modules.usuarios.infrastructure.security import \
    BcryptPasswordHasher

router = APIRouter(prefix="/api/v1/onboarding", tags=["SaaS Onboarding"])


@router.post(
    "/", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED
)
async def registrar_restaurante(
    request: OnboardingRequest, db: AsyncSession = Depends(get_db)
):
    # 1. Inyección de dependencias
    repository = PostgresRestauranteRepository(session=db)
    hasher = BcryptPasswordHasher()
    use_case = RegistrarRestauranteSaaSUseCase(repository=repository, hasher=hasher)

    try:
        # 2. Ejecutamos el caso de uso pasando los diccionarios usando Pydantic V2 (model_dump)
        restaurante, admin = await use_case.ejecutar(
            datos_restaurante=request.restaurante.model_dump(),
            datos_admin=request.admin.model_dump(),
        )

        # 3. Mapeamos la respuesta
        return OnboardingResponse(
            restaurante=RestauranteResponse(
                id=restaurante.id,
                nombre_comercial=restaurante.nombre_comercial,
                email_corporativo=restaurante.email_corporativo,
                estado=restaurante.estado,
                fecha_registro=restaurante.fecha_registro,
            ),
            admin=UsuarioSaaSResponse(
                id=admin.id,
                restaurante_id=admin.restaurante_id,
                nombre=admin.nombre,
                email=admin.email,
                rol=admin.rol.value,
                estado=admin.estado,
            ),
        )

    except ValueError as e:
        # Capturamos los errores de negocio (Ej: Email o RUC duplicado) y lanzamos 400
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
