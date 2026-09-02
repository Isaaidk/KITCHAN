import httpx
from fastapi import HTTPException
from src.kitchan.modules.integraciones.uber.domain.ports import UberApiPort

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

    async def accept_order(self, order_id: str, access_token: str, reason: str = "Accepted") -> bool:
        url = f"https://test-api.uber.com/v1/eats/orders/{order_id}/accept_pos_order"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient() as client:
            # Uber pide un JSON con el motivo (reason)
            respuesta = await client.post(url, headers=headers, json={"reason": reason})
            
        if respuesta.status_code not in (200, 204):
            print(f"❌ Error al aceptar orden {order_id}: {respuesta.text}")
            raise HTTPException(status_code=respuesta.status_code, detail="No se pudo aceptar la orden en Uber")
            
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

        if respuesta.status_code != 200:
            print(
                f"❌ Error al marcar orden {order_id} "
                f"como READY: {respuesta.text}"
            )

            raise HTTPException(
                status_code=respuesta.status_code,
                detail=(
                    "No se pudo marcar la orden "
                    "como lista en Uber"
                )
            )

        return True