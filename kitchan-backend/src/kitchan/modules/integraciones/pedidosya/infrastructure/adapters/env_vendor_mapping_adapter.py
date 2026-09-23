"""Infraestructura de PedidosYa: mapeo remoteId -> restaurante_id, cargado
desde una variable de entorno (JSON). El alta de cada vendor en PedidosYa es
un proceso manual (NDA + formulario con el contacto de cuenta), no un flujo
de autodescubrimiento en tiempo de ejecución como el store-mapping de Uber
(que se arma después de un OAuth) — por eso este adaptador es estático en
vez de apoyarse en Redis.
"""

import json
import os
from typing import Optional

from src.kitchan.modules.integraciones.pedidosya.domain.ports import (
    PedidosYaVendorMappingPort,
)


class EnvPedidosYaVendorMappingAdapter(PedidosYaVendorMappingPort):
    def __init__(self):
        raw = os.getenv("PEDIDOSYA_REMOTE_ID_MAP", "{}")
        try:
            self._mapa: dict[str, str] = json.loads(raw)
        except json.JSONDecodeError:
            print(f"⚠️ [PEDIDOSYA] PEDIDOSYA_REMOTE_ID_MAP no es JSON válido: {raw!r}")
            self._mapa = {}

    async def get_restaurante_id(self, remote_id: str) -> Optional[str]:
        return self._mapa.get(remote_id)
