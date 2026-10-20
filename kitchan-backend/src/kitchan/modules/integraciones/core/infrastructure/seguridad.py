"""Seguridad compartida de las acciones del KDS sobre pedidos de integraciones
(aceptar, rechazar, cancelar, marcar listo) en Uber, PedidosYa y Rappi.

Cada ruta exige:
1. Un usuario de KITCHAN autenticado (Bearer JWT).
2. Que el pedido pertenezca al restaurante de ese usuario. Sin esto, alguien
   con sesión en un restaurante podría operar pedidos de otro conociendo su
   id externo, porque las credenciales de PedidosYa y Rappi son de
   aplicación y no por restaurante.
"""

from fastapi import Depends, HTTPException, status

from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.pedidos.infrastructure.dependencias import get_order_dispatcher
from src.kitchan.modules.usuarios.infrastructure.auth_dependencies import (
    obtener_usuario_actual,
)


def usuario_duenio_del_pedido(origen: str):
    """Dependencia factory: valida sesión y propiedad del pedido `order_id`
    (parámetro de ruta) para la plataforma `origen`. Retorna los claims."""

    async def verificar(
        order_id: str,
        usuario: dict = Depends(obtener_usuario_actual),
        order_dispatcher: OrderDispatcherPort = Depends(get_order_dispatcher),
    ) -> dict:
        pertenece = await order_dispatcher.order_belongs_to_restaurant(
            origen, order_id, usuario["restaurante_id"]
        )
        if not pertenece:
            # 404 y no 403: no se revela si el pedido existe en otro restaurante.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado"
            )
        return usuario

    return verificar


def verificar_restaurante_del_usuario(restaurante_id: str, usuario: dict) -> None:
    """Para rutas que reciben `restaurante_id` (Uber): debe ser el del usuario."""
    if str(restaurante_id) != str(usuario.get("restaurante_id")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos sobre este restaurante",
        )
