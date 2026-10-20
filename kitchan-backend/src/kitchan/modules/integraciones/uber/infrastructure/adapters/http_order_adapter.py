import httpx
from fastapi import HTTPException
from src.kitchan.modules.integraciones.uber.domain.ports import UberApiPort
from datetime import datetime, timedelta, timezone


class UberHttpAdapter(UberApiPort):

    async def get_order_details(self, order_id: str, access_token: str) -> dict:

        # --- 🧪 INTERCEPTOR DE PRUEBAS (Evita el 401 de Uber) ---
        # --------------------------------------------------------

        # Código real para producción
        url = f"https://test-api.uber.com/v2/eats/order/{order_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            respuesta = await client.get(url, headers=headers)

        if respuesta.status_code != 200:
            raise HTTPException(
                status_code=respuesta.status_code,
                detail=f"Error en Uber: {respuesta.text}",
            )

        return respuesta.json()

    async def accept_order(
        self, order_id: str, access_token: str, reason: str = "Accepted"
    ) -> bool:
        # Endpoint real de Eats POS (v1/eats/orders, no v1/delivery/order —
        # ese es de Uber Direct, un producto distinto). Confirmado contra
        # developer.uber.com/docs/eats/references/api/v1/post-eats-order-orderid-acceptposorder:
        # requiere "reason" y opcionalmente "pickup_time" como unix timestamp
        # (no un ISO string) — así es como Uber conoce el tiempo estimado de
        # entrega; no existe un endpoint separado para "marcar listo".
        url = (
            f"https://test-api.uber.com" f"/v1/eats/orders/{order_id}/accept_pos_order"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        pickup_time = int(
            (datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()
        )

        payload = {
            "reason": reason,
            "pickup_time": pickup_time,
        }

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(url, headers=headers, json=payload)

        print(f"📡 [UBER ACCEPT] order_id={order_id}")
        print(f"📡 [UBER ACCEPT] status={respuesta.status_code}")
        print(f"📡 [UBER ACCEPT] response={respuesta.text}")
        print(f"📡 [UBER ACCEPT] pickup_time={pickup_time}")

        if respuesta.status_code not in (200, 204):
            raise HTTPException(
                status_code=respuesta.status_code,
                detail={
                    "error": "No se pudo aceptar la orden en Uber",
                    "uber_response": respuesta.text,
                },
            )

        return True

    async def deny_order(
        self, order_id: str, access_token: str, reason: str, explanation: str
    ) -> bool:
        # Mismo error que accept_order tenía: "orders" es plural y va en v1,
        # no v2/eats/order (singular). Confirmado contra developer.uber.com/
        # docs/eats/references/api/v1/post-eats-order-orderid-denyposorder.
        url = f"https://test-api.uber.com/v1/eats/orders/{order_id}/deny_pos_order"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Motivos válidos según Uber: STORE_CLOSED, POS_NOT_READY, POS_OFFLINE,
        # ITEM_AVAILABILITY, MISSING_ITEM, MISSING_INFO, PRICING, CAPACITY,
        # ADDRESS, SPECIAL_INSTRUCTIONS, OTHER. El campo es "reason.code", no
        # "reason_code" a nivel raíz ni "out_of_item_details".
        payload = {
            "reason": {
                "code": reason,
                "explanation": explanation,
            }
        }

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(url, headers=headers, json=payload)

        if respuesta.status_code not in (200, 204):
            print(f"❌ Error al rechazar orden {order_id}: {respuesta.text}")
            raise HTTPException(
                status_code=respuesta.status_code,
                detail="No se pudo rechazar la orden en Uber",
            )

        return True

    async def cancel_order(
        self, order_id: str, access_token: str, reason: str, details: str | None = None
    ) -> bool:
        # Cancela un pedido YA ACEPTADO (a diferencia de deny_order, que solo
        # aplica antes de aceptar). Endpoint confirmado contra
        # developer.uber.com/docs/eats/references/api/v1/post-eats-order-orderid-cancel
        # — "orders" plural, v1/eats, no v1/delivery/order.
        url = f"https://test-api.uber.com/v1/eats/orders/{order_id}/cancel"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Motivos válidos: OUT_OF_ITEMS, KITCHEN_CLOSED,
        # CUSTOMER_CALLED_TO_CANCEL, RESTAURANT_TOO_BUSY,
        # CANNOT_COMPLETE_CUSTOMER_NOTE, OTHER (con "details" opcional).
        payload: dict = {"reason": reason}
        if details:
            payload["details"] = details

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(url, headers=headers, json=payload)

        print(f"📡 [UBER CANCEL] order_id={order_id}")
        print(f"📡 [UBER CANCEL] status={respuesta.status_code}")
        print(f"📡 [UBER CANCEL] response={respuesta.text}")

        if respuesta.status_code not in (200, 204):
            raise HTTPException(
                status_code=respuesta.status_code,
                detail={
                    "error": "No se pudo cancelar la orden en Uber",
                    "uber_response": respuesta.text,
                },
            )

        return True

    async def mark_order_ready(self, order_id: str, access_token: str) -> bool:
        # La API de Eats POS (v1/eats/orders) NO tiene un endpoint para
        # "marcar listo": el tiempo estimado de entrega ya se informa en
        # accept_pos_order (campo pickup_time). Confirmado revisando la
        # referencia completa de endpoints de orders en developer.uber.com
        # (accept_pos_order, deny_pos_order, cancel, cart, restaurantdelivery/
        # status — este último es solo para delivery gestionado por el
        # merchant, no aplica acá). "Listo" es un estado interno de KITCHAN;
        # no hay nada que llamar en Uber en este paso.
        print(
            f"ℹ️ [UBER READY] {order_id}: no existe endpoint de Eats POS "
            "para 'listo' (el pickup_time ya se envió en el accept). "
            "Solo se actualiza el estado interno de KITCHAN."
        )
        return True

    async def get_delivery_order_details(
        self, order_id: str, access_token: str
    ) -> dict:

        url = f"https://test-api.uber.com" f"/v1/delivery/order/{order_id}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            respuesta = await client.get(url, headers=headers)

        if respuesta.status_code != 200:
            print(
                f"❌ Error obteniendo estado delivery " f"{order_id}: {respuesta.text}"
            )

            raise HTTPException(
                status_code=respuesta.status_code,
                detail=("No se pudo obtener el estado " "delivery de la orden en Uber"),
            )

        return respuesta.json()
