import httpx
from fastapi import HTTPException
from typing import Dict, Any

# Importamos los puertos necesarios
from src.kitchan.modules.pedidos.domain.ports.uber_order_port import UberOrderPort
from src.kitchan.modules.integraciones.uber.domain.ports import UberTokenCachePort
class UberHttpOrderAdapter(UberOrderPort):
    """
    Adaptador de infraestructura que se comunica con la API REST de Uber Eats.
    """

    def __init__(self, token_adapter: UberTokenCachePort, base_url: str):
        # Inyectamos el adaptador de tokens para resolver el multi-tenant
        self.token_adapter = token_adapter
        self.base_url = base_url

    async def _get_headers(self, restaurante_id: str) -> dict:
        """
        Método privado para obtener el token correcto del tenant.
        Usamos el App Token (Client Credentials) que ya validamos que tiene
        permisos de escritura sobre la tienda provisionada.
        """
        token = await self.token_adapter.get_app_token(restaurante_id)
        if not token:
            raise HTTPException(
                status_code=401, 
                detail=f"No hay token operativo para el restaurante {restaurante_id}. Re-autenticar."
            )
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def aceptar_pedido(self, order_id: str, restaurante_id: str) -> Dict[str, Any]:
        """
        Llama al endpoint v2 de Uber para aceptar la orden (POS Acknowledgment).
        """
        headers = await self._get_headers(restaurante_id)
        url = f"{self.base_url}/v2/eats/orders/{order_id}/accept_pos_order"
        
        # El payload para aceptar suele estar vacío a menos que se envíen tiempos estimados
        payload = {}

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(url, json=payload, headers=headers, timeout=15)
        
        if respuesta.status_code not in (200, 204):
            raise HTTPException(
                status_code=respuesta.status_code,
                detail={"error": "Uber rechazó la aceptación", "detalle": respuesta.text}
            )
        
        return {"status": "accepted", "uber_order_id": order_id}

    async def rechazar_pedido(self, order_id: str, restaurante_id: str, razon: str) -> Dict[str, Any]:
        """
        Llama al endpoint v2 de Uber para rechazar la orden.
        Uber exige un motivo (reason). Ej: "OUT_OF_ITEM", "TOO_BUSY", etc.
        """
        headers = await self._get_headers(restaurante_id)
        url = f"{self.base_url}/v2/eats/orders/{order_id}/deny_pos_order"
        
        payload = {
            "reason": {
                "explanation": razon # Uber documenta códigos específicos para esto
            }
        }

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(url, json=payload, headers=headers, timeout=15)
        
        if respuesta.status_code not in (200, 204):
            raise HTTPException(
                status_code=respuesta.status_code,
                detail={"error": "Fallo al rechazar en Uber", "detalle": respuesta.text}
            )
        
        return {"status": "denied", "uber_order_id": order_id}