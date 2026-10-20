"""Infraestructura de PedidosYa: adaptador que implementa PedidosYaApiPort
contra el Integration Middleware API real de Delivery Hero/PedidosYa (la API
que ya existe y que nosotros consumimos, equivalente a UberHttpAdapter).
"""

import os

import httpx
from fastapi import HTTPException

from src.kitchan.modules.integraciones.pedidosya.domain.ports import PedidosYaApiPort

# Dominio real de staging documentado por PedidosYa/Delivery Hero
# (integration-middleware.stg.restaurant-partners.com). No hay dominio de
# producción confirmado en la documentación disponible; sobreescribir con
# PEDIDOSYA_API_BASE una vez que el contacto de cuenta entregue el dominio
# productivo tras el alta manual (NDA + formulario).
PEDIDOSYA_API_BASE_DEFAULT = (
    "https://integration-middleware.stg.restaurant-partners.com"
)


class PedidosYaHttpAdapter(PedidosYaApiPort):
    def __init__(self):
        self.base_url = os.getenv("PEDIDOSYA_API_BASE", PEDIDOSYA_API_BASE_DEFAULT)
        self.username = os.getenv("PEDIDOSYA_PLUGIN_USERNAME")
        self.password = os.getenv("PEDIDOSYA_PLUGIN_PASSWORD")

    def _auth(self) -> httpx.BasicAuth:
        # TODO: el resumen de documentación disponible solo confirma que se
        # asigna un "plugin username" durante el alta; el mecanismo exacto de
        # auth del Integration Middleware API (Basic Auth vs API key propia)
        # no está confirmado — verificar contra el spec de pos-middleware-api
        # antes de producción. Basic Auth es el placeholder más razonable
        # dado lo que sí se documentó.
        if not self.username or not self.password:
            raise HTTPException(
                status_code=401,
                detail="Credenciales de PedidosYa (plugin username/password) no configuradas.",
            )
        return httpx.BasicAuth(self.username, self.password)

    async def update_order_status(
        self, remote_order_id: str, status: str, reason: str | None = None
    ) -> bool:
        # TODO: path y forma exacta del payload a confirmar contra
        # pos-middleware-api ("Update Order Status").
        url = f"{self.base_url}/order/{remote_order_id}/status"
        payload: dict = {"status": status}
        if reason:
            payload["reason"] = reason

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(
                url, json=payload, auth=self._auth(), timeout=15
            )

        print(
            f"📡 [PEDIDOSYA STATUS] order_id={remote_order_id} status={status} -> {respuesta.status_code}"
        )

        if respuesta.status_code not in (200, 204):
            raise HTTPException(
                status_code=respuesta.status_code,
                detail={
                    "error": "No se pudo actualizar el estado en PedidosYa",
                    "respuesta": respuesta.text,
                },
            )
        return True

    async def mark_order_prepared(self, remote_order_id: str) -> bool:
        # TODO: path exacto a confirmar contra pos-middleware-api ("Mark
        # Order as Prepared").
        url = f"{self.base_url}/order/{remote_order_id}/prepared"

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(url, auth=self._auth(), timeout=15)

        print(
            f"📡 [PEDIDOSYA PREPARED] order_id={remote_order_id} -> {respuesta.status_code}"
        )

        if respuesta.status_code not in (200, 204):
            raise HTTPException(
                status_code=respuesta.status_code,
                detail={
                    "error": "No se pudo marcar el pedido como listo en PedidosYa",
                    "respuesta": respuesta.text,
                },
            )
        return True
