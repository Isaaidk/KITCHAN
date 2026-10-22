"""Shared kernel: quién está ejecutando la petición actual.

La dependencia de autenticación deja aquí el id del usuario; así los adaptadores
(por ejemplo, el repositorio de pedidos) pueden registrar "quién aceptó este
pedido" sin que cada endpoint de cada canal tenga que pasarlo a mano.
"""

from contextvars import ContextVar
from typing import Optional

_usuario_id: ContextVar[Optional[str]] = ContextVar("usuario_id_actual", default=None)


def fijar_usuario_actual(usuario_id: Optional[str]) -> None:
    _usuario_id.set(usuario_id)


def usuario_actual_id() -> Optional[str]:
    return _usuario_id.get()
