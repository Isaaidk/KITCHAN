import hmac
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel

from src.kitchan.modules.facturacion.application.facturar_pedido import (
    ActualizarFacturaDesdeOdooUseCase,
    ConciliarFacturasPendientesUseCase,
    ConsultarFacturaPedidoUseCase,
    FacturarPedidoUseCase,
)
from src.kitchan.modules.facturacion.domain.entities import FacturaPedido
from src.kitchan.modules.facturacion.domain.exceptions import (
    OdooError,
    OdooNoConfiguradoError,
    PedidoNoEncontradoError,
    PedidoNoFacturableError,
)
from src.kitchan.modules.facturacion.domain.ports import OdooFacturacionPort
from src.kitchan.modules.facturacion.infrastructure.dependencias import (
    get_actualizar_use_case,
    get_conciliar_use_case,
    get_consultar_use_case,
    get_facturar_use_case,
    get_odoo,
)
from src.kitchan.modules.usuarios.domain.entities import RolUsuario
from src.kitchan.modules.usuarios.infrastructure.auth_dependencies import (
    obtener_usuario_actual,
    requiere_rol,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/facturacion", tags=["Facturación"])


class FacturaResponse(BaseModel):
    pedido_id: str
    numero: Optional[str] = None
    estado: str
    total: float
    numero_autorizacion: Optional[str] = None
    fecha_autorizacion: Optional[datetime] = None
    mensaje_error: Optional[str] = None

    @staticmethod
    def from_domain(factura: FacturaPedido) -> "FacturaResponse":
        return FacturaResponse(
            pedido_id=factura.pedido_id,
            numero=factura.numero,
            estado=factura.estado.value,
            total=factura.total,
            numero_autorizacion=factura.numero_autorizacion,
            fecha_autorizacion=factura.fecha_autorizacion,
            mensaje_error=factura.mensaje_error,
        )


class EstadoOdooResponse(BaseModel):
    configurado: bool


class ConciliacionResponse(BaseModel):
    actualizadas: int


@router.get("/estado", response_model=EstadoOdooResponse)
async def estado_odoo(
    _usuario: dict = Depends(obtener_usuario_actual),
    odoo: OdooFacturacionPort = Depends(get_odoo),
):
    return EstadoOdooResponse(configurado=odoo.configurado())


@router.get("/pedidos/{pedido_id}", response_model=Optional[FacturaResponse])
async def factura_del_pedido(
    pedido_id: str,
    usuario_actual: dict = Depends(obtener_usuario_actual),
    use_case: ConsultarFacturaPedidoUseCase = Depends(get_consultar_use_case),
):
    """La factura del pedido, o null si todavía no se facturó."""
    factura = await use_case.ejecutar(pedido_id, usuario_actual["restaurante_id"])
    return FacturaResponse.from_domain(factura) if factura else None


@router.post("/pedidos/{pedido_id}", response_model=FacturaResponse)
async def facturar_pedido(
    pedido_id: str,
    usuario_actual: dict = Depends(obtener_usuario_actual),
    use_case: FacturarPedidoUseCase = Depends(get_facturar_use_case),
):
    """Emite en Odoo la factura del pedido (Odoo la envía al SRI). Si ya
    existe, la devuelve; si quedó con error, reintenta el envío al SRI."""
    try:
        factura = await use_case.ejecutar(pedido_id, usuario_actual["restaurante_id"])
    except PedidoNoEncontradoError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except PedidoNoFacturableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    except OdooNoConfiguradoError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        )
    except OdooError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))
    return FacturaResponse.from_domain(factura)


@router.post("/conciliar", response_model=ConciliacionResponse)
async def conciliar_facturas(
    _usuario: dict = Depends(requiere_rol(RolUsuario.ADMIN.value)),
    use_case: ConciliarFacturasPendientesUseCase = Depends(get_conciliar_use_case),
):
    """Revisa ya en Odoo las facturas que esperan al SRI (lo mismo que hace
    el barrido periódico)."""
    return ConciliacionResponse(actualizadas=await use_case.ejecutar())


def _token_valido(token: str) -> bool:
    esperado = os.getenv("ODOO_WEBHOOK_TOKEN")
    return bool(esperado) and hmac.compare_digest(token, esperado)


@router.post("/odoo/webhook/{token}", include_in_schema=False)
async def webhook_odoo(
    token: str,
    cuerpo: dict = Body(default_factory=dict),
    use_case: ActualizarFacturaDesdeOdooUseCase = Depends(get_actualizar_use_case),
):
    """Lo llama la regla de automatización de Odoo ("Enviar notificación de
    webhook") cuando cambia el estado SRI de una factura. Odoo no firma sus
    webhooks, así que se autentica con un token secreto en la URL y, además,
    el cuerpo no se usa como verdad: solo se toma el id y se relee la factura
    en Odoo con la API."""
    if not _token_valido(token):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if cuerpo.get("_model") != "account.move":
        return {"ok": True}
    try:
        odoo_move_id = int(cuerpo.get("_id"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Falta el id de la factura (_id).",
        )
    try:
        await use_case.ejecutar(odoo_move_id)
    except OdooError as error:
        logger.warning("Webhook de Odoo para la factura %s: %s", odoo_move_id, error)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))
    return {"ok": True}
