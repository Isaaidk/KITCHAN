import os
import json

from fastapi import APIRouter, Request, Header, HTTPException, Depends
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from src.kitchan.core.database import get_db
from src.kitchan.modules.pedidos.application.crear_pedido_service import (
    CrearPedidoUseCase
)
from src.kitchan.modules.pedidos.application.actualizar_estado_pedido_service import (
    ActualizarEstadoPedidoUseCase
)

from src.kitchan.modules.pedidos.infrastructure.repository import (
    PostgresPedidoRepository
)
from src.kitchan.modules.pedidos.infrastructure.eventos.redis_publisher import (
    RedisPublisherAdapter
)

from src.kitchan.modules.integraciones.uber.infrastructure.security.hmac_validator import (
    verify_uber_signature
)
from src.kitchan.modules.integraciones.uber.domain.models import (
    UberWebhookPayload
)

from src.kitchan.modules.integraciones.uber.application.webhook_use_cases import (
    UberWebhookUseCase
)
from src.kitchan.modules.integraciones.uber.infrastructure.adapters.redis_token_adapter import (
    RedisUberTokenAdapter
)


from src.kitchan.modules.integraciones.uber.infrastructure.adapters.http_order_adapter import (
    UberHttpAdapter
)

from src.kitchan.modules.pedidos.infrastructure.adapters.integraciones_dispatcher import (
    PedidosIntegracionesAdapter
)

load_dotenv()


router = APIRouter(
    prefix="/api/v1/integraciones/uber/webhook",
    tags=["Integraciones - Uber Eats Webhook"]
)


UBER_WEBHOOK_SECRET = os.getenv("UBER_WEBHOOK_SECRET")

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)


# ============================================================
# VALIDACIÓN HMAC
# ============================================================

async def validate_webhook_signature(
    request: Request,
    x_uber_signature: str | None = Header(
        default=None,
        description="Firma criptográfica enviada por Uber"
    )
):
    """
    Valida la firma HMAC enviada por Uber.

    Uber envía el webhook mediante POST y la firma
    permite verificar que realmente proviene de Uber.
    """

    if not x_uber_signature:
        raise HTTPException(
            status_code=401,
            detail="Firma de Uber faltante"
        )

    if not UBER_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Falta configurar UBER_WEBHOOK_SECRET"
        )

    raw_body = await request.body()

    is_valid = verify_uber_signature(
        client_secret=UBER_WEBHOOK_SECRET,
        raw_body=raw_body,
        signature=x_uber_signature
    )

    if not is_valid:

        print(
            "🚨 ALERTA: "
            "Intento de webhook falsificado detectado."
        )

        raise HTTPException(
            status_code=403,
            detail="Firma de Uber inválida"
        )

    return raw_body


# ============================================================
# DEPENDENCY INJECTION
# ============================================================
def get_webhook_use_case(
    db: AsyncSession = Depends(get_db),
) -> UberWebhookUseCase:
    token_adapter = RedisUberTokenAdapter(
        redis_url=REDIS_URL
    )

    api_adapter = UberHttpAdapter()

    repo_pedidos = PostgresPedidoRepository(session=db)
    notificador = RedisPublisherAdapter(redis_url=REDIS_URL)

    crear_pedido_use_case = CrearPedidoUseCase(
        repository=repo_pedidos, notificador=notificador
    )
    actualizar_estado_use_case = ActualizarEstadoPedidoUseCase(
        repository=repo_pedidos, notificador=notificador
    )

    dispatcher_adapter = PedidosIntegracionesAdapter(
        use_case=crear_pedido_use_case,
        actualizar_estado_use_case=actualizar_estado_use_case,
    )

    return UberWebhookUseCase(
        token_cache=token_adapter,
        uber_api=api_adapter,
        order_dispatcher=dispatcher_adapter
    )
# ============================================================
# WEBHOOK UBER
# ============================================================

@router.post("")
async def receive_uber_webhook(
    valid_body: bytes = Depends(
        validate_webhook_signature
    ),

    use_case: UberWebhookUseCase = Depends(
        get_webhook_use_case
    )
):

    """
    Endpoint receptor de eventos de Uber Eats.

    IMPORTANTE:

    Uber NO envía restaurante_id como query parameter.

    El webhook debe identificar el restaurante utilizando
    la información incluida en el evento de Uber.
    """

    print("\n")
    print("=" * 60)
    print("🔔 WEBHOOK DE UBER RECIBIDO")
    print("=" * 60)

    print("BODY RAW:")

    print(
        valid_body.decode(
            "utf-8",
            errors="replace"
        )
    )

    print("=" * 60)


    # ========================================================
    # PARSEAR JSON
    # ========================================================

    try:

        payload_dict = json.loads(
            valid_body
        )

    except json.JSONDecodeError as error:

        print(
            "❌ Error convirtiendo webhook a JSON:",
            error
        )

        raise HTTPException(
            status_code=422,
            detail="El payload recibido no es JSON válido"
        )


    event_type = payload_dict.get("event_type")
    print("EVENT TYPE:")
    print(event_type)

    # Uber envía muchas familias de eventos a esta misma URL (store.provisioned,
    # menu updates, etc.) con una forma distinta a UberWebhookPayload. Solo
    # los eventos de pedidos nos interesan; el resto se reconoce con 200 sin
    # intentar validarlo, para no fallar con 422 en algo que no vamos a usar.
    EVENTOS_MANEJADOS = {"orders.notification", "orders.cancel", "delivery.state_changed"}
    if event_type not in EVENTOS_MANEJADOS:
        print(f"ℹ️ Evento '{event_type}' no es de pedidos, se reconoce sin procesar.")
        return {"status": "ignored", "event_type": event_type}

    # ========================================================
    # VALIDAR MODELO
    # ========================================================

    try:

        payload_model = UberWebhookPayload(
            **payload_dict
        )

    except Exception as error:

        print(
            "❌ Payload incompatible con "
            "UberWebhookPayload:"
        )

        print(error)

        raise HTTPException(
            status_code=422,
            detail={
                "error": "INVALID_UBER_PAYLOAD",
                "mensaje": (
                    "El payload recibido de Uber "
                    "no coincide con UberWebhookPayload"
                )
            }
        )


    # ========================================================
    # PROCESAR EVENTO
    # ========================================================

    try:

        await use_case.process_notification(
            payload_model
        )

    except Exception as error:

        print(
            "❌ Error procesando evento Uber:"
        )

        print(error)

        raise


    # ========================================================
    # RESPUESTA A UBER
    # ========================================================

    print(
        "✅ Evento Uber procesado correctamente"
    )

    return {
        "status": "success"
    }