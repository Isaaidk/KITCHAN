# Adaptador de entrada: dependencias de FastAPI reutilizables para proteger rutas.
# Extraen y validan el JWT del header Authorization, y restringen endpoints por rol,
# reutilizando el mismo ITokenGenerator/JWTTokenGenerator que ya firma los tokens en el login.
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.kitchan.core.contexto_usuario import fijar_usuario_actual
from src.kitchan.modules.usuarios.infrastructure.security import JWTTokenGenerator

_bearer_scheme = HTTPBearer(auto_error=False)


async def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """Valida el Bearer token y retorna sus claims (sub, id, rol, restaurante_id)."""
    if credenciales is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )

    token_generator = JWTTokenGenerator()
    try:
        claims = token_generator.decodificar_token(credenciales.credentials)
        # Queda disponible para registrar quién hace cada acción (ver core/contexto_usuario).
        fijar_usuario_actual(claims.get("id"))
        return claims
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


def requiere_rol(*roles_permitidos: str):
    """Dependencia factory: exige un usuario autenticado cuyo rol esté permitido."""

    async def verificador(
        claims: dict = Depends(obtener_usuario_actual),
    ) -> dict:
        if claims.get("rol") not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para acceder a este recurso",
            )
        return claims

    return verificador
