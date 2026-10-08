"""Traducción de errores de las plataformas externas a respuestas HTTP.

Un 401 en la API de KITCHAN significa "tu sesión de KITCHAN no es válida" y
el frontend cierra la sesión al recibirlo. Por eso los rechazos de Uber,
Rappi o PedidosYa (credenciales faltantes, vencidas o sin permiso sobre la
tienda) nunca deben llegar al frontend como 401/403: son fallas de un
servicio externo, no del usuario.
"""

from fastapi import HTTPException, status


def error_de_plataforma(error: HTTPException, plataforma: str) -> HTTPException:
    """Convierte un 401/403 de la plataforma en 502; el resto queda igual."""
    if error.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": f"{plataforma} rechazó la autenticación de KITCHAN.",
                "respuesta": error.detail,
            },
        )
    return error
