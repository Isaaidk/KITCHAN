"""Infraestructura de PedidosYa: endpoint HTTP que Delivery Hero llama para
entregarnos un pedido nuevo (POST /order/{remoteId}, documentado como
"Dispatch Order" en la Plugin API). Es el equivalente arquitectónico al
webhook_api.py de Uber: valida la autenticación entrante, parsea y valida el
payload, y delega en el caso de uso — la diferencia es de transporte
(PedidosYa nos hace un POST directo por vendor, con remoteId en la URL, en
vez de un evento genérico con metadata como Uber).
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from src.kitchan.modules.integraciones.pedidosya.application.order_dispatch_use_case import (
    PedidosYaOrderDispatchUseCase,
)
from src.kitchan.modules.integraciones.pedidosya.domain.models import (
    OrderDispatchAcknowledgedResponse,
    PedidosYaOrderPayload,
)
from src.kitchan.modules.integraciones.pedidosya.domain.ports import (
    PedidosYaVendorMappingPort,
)
from src.kitchan.modules.integraciones.pedidosya.infrastructure.adapters.env_vendor_mapping_adapter import (
    EnvPedidosYaVendorMappingAdapter,
)
from src.kitchan.modules.integraciones.pedidosya.infrastructure.security.jwt_validator import (
    validar_jwt_pedidosya,
)
from src.kitchan.modules.integraciones.core.domain.inter_module_ports import (
    OrderDispatcherPort,
)
from src.kitchan.modules.pedidos.infrastructure.dependencias import get_order_dispatcher

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/integraciones/pedidosya",
    tags=["Integraciones - PedidosYa Dispatch"],
)


# ============================================================
# DEPENDENCY INJECTION
# ============================================================
def get_order_dispatch_use_case(
    order_dispatcher: OrderDispatcherPort = Depends(get_order_dispatcher),
) -> PedidosYaOrderDispatchUseCase:
    return PedidosYaOrderDispatchUseCase(order_dispatcher=order_dispatcher)


def get_vendor_mapping() -> PedidosYaVendorMappingPort:
    return EnvPedidosYaVendorMappingAdapter()


# ============================================================
# DISPATCH ORDER
# ============================================================
@router.post("/order/{remote_id}", response_model=OrderDispatchAcknowledgedResponse)
async def dispatch_order_pedidosya(
    remote_id: str,
    request: Request,
    _claims: dict = Depends(validar_jwt_pedidosya),
    vendor_mapping: PedidosYaVendorMappingPort = Depends(get_vendor_mapping),
    use_case: PedidosYaOrderDispatchUseCase = Depends(get_order_dispatch_use_case),
):
    """
    Endpoint receptor de pedidos de PedidosYa (Delivery Hero nos hace este
    POST; no es un webhook que nosotros registramos con una URL, sino la
    "Base URL" acordada durante el alta manual).
    """
    body_raw = await request.body()

    try:
        payload_dict = json.loads(body_raw)
    except json.JSONDecodeError as error:
        logger.warning("Payload de PedidosYa no es JSON válido: %s", error)
        raise HTTPException(
            status_code=422, detail="El payload recibido no es JSON válido"
        )

    try:
        payload_model = PedidosYaOrderPayload(**payload_dict)
    except Exception as error:
        logger.warning("Payload incompatible con PedidosYaOrderPayload: %s", error)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INVALID_PEDIDOSYA_PAYLOAD",
                "mensaje": "El payload recibido de PedidosYa no coincide con el schema esperado",
            },
        )

    restaurante_id = await vendor_mapping.get_restaurante_id(remote_id)
    if not restaurante_id:
        logger.warning(
            "remoteId '%s' no está mapeado a ningún restaurante de KITCHAN.", remote_id
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "mensaje": f"remoteId '{remote_id}' no está dado de alta en KITCHAN.",
            },
        )

    try:
        return await use_case.procesar_dispatch(restaurante_id, payload_model)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Error inesperado procesando dispatch de PedidosYa para remoteId=%s",
            remote_id,
        )
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVICE_ERROR"})
