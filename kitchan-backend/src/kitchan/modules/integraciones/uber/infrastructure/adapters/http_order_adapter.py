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
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient() as client:
            respuesta = await client.get(url, headers=headers)
            
        if respuesta.status_code != 200:
            raise HTTPException(status_code=respuesta.status_code, detail=f"Error en Uber: {respuesta.text}")
            
        return respuesta.json()



    async def accept_order(
        self,
        order_id: str,
        access_token: str,
        reason: str = "Accepted"
    ) -> bool:

        url = (
            f"https://test-api.uber.com"
            f"/v1/delivery/order/{order_id}/accept"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        ready_for_pickup_time = (
            datetime.now(timezone.utc) + timedelta(minutes=10)
        ).isoformat()

        payload = {
            "ready_for_pickup_time": ready_for_pickup_time,
            "accepted_by": "KITCHAN"
        }

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(
                url,
                headers=headers,
                json=payload
            )

        print(f"📡 [UBER ACCEPT] order_id={order_id}")
        print(f"📡 [UBER ACCEPT] status={respuesta.status_code}")
        print(f"📡 [UBER ACCEPT] response={respuesta.text}")
        print(
            f"📡 [UBER ACCEPT] ready_for_pickup_time="
            f"{ready_for_pickup_time}"
        )

        if respuesta.status_code not in (200, 204):
            raise HTTPException(
                status_code=respuesta.status_code,
                detail={
                    "error": "No se pudo aceptar la orden en Uber",
                    "uber_response": respuesta.text
                }
            )

        return True
    async def deny_order(self, order_id: str, access_token: str, reason: str, explanation: str) -> bool:
        url = f"https://test-api.uber.com/v2/eats/order/{order_id}/deny_pos_order"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        
        # Motivos válidos según Uber: ITEM_OUT_OF_STOCK, KITCHEN_CLOSED, OTHER
        payload = {
            "reason": {
                "explanation": explanation,
                "out_of_item_details": {"item_ids": []} # Vacío si cancelamos todo
            },
            "reason_code": reason
        }
        
        async with httpx.AsyncClient() as client:
            respuesta = await client.post(url, headers=headers, json=payload)
            
        if respuesta.status_code not in (200, 204):
            print(f"❌ Error al rechazar orden {order_id}: {respuesta.text}")
            raise HTTPException(status_code=respuesta.status_code, detail="No se pudo rechazar la orden en Uber")
            
        return True

    async def mark_order_ready(
        self,
        order_id: str,
        access_token: str
    ) -> bool:

        url = (
            f"https://test-api.uber.com"
            f"/v1/delivery/order/{order_id}/ready"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(
                url,
                headers=headers,
                json={}
            )

        print(
    f"📡 [UBER READY] order_id={order_id}"
)
        print(
            f"📡 [UBER READY] status={respuesta.status_code}"
        )
        print(
            f"📡 [UBER READY] response={respuesta.text}"
        )

        if respuesta.status_code != 200:
            raise HTTPException(
                status_code=respuesta.status_code,
                detail={
                    "error": "No se pudo marcar la orden como lista en Uber",
                    "uber_response": respuesta.text
                }
            )

        print(
            f"✅ [UBER READY] Orden {order_id} "
            "aceptada por Uber como READY"
        )

        return True

    async def get_delivery_order_details(
            self,
            order_id: str,
            access_token: str
        ) -> dict:

            url = (
                f"https://test-api.uber.com"
                f"/v1/delivery/order/{order_id}"
            )

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                respuesta = await client.get(
                    url,
                    headers=headers
                )

            if respuesta.status_code != 200:
                print(
                    f"❌ Error obteniendo estado delivery "
                    f"{order_id}: {respuesta.text}"
                )

                raise HTTPException(
                    status_code=respuesta.status_code,
                    detail=(
                        "No se pudo obtener el estado "
                        "delivery de la orden en Uber"
                    )
                )

            return respuesta.json()