"""Infraestructura de Rappi: mapeo store_id de Rappi -> restaurante_id,
cargado desde una variable de entorno (JSON). Igual que en PedidosYa, el
alta de cada tienda en Rappi es manual, por eso este adaptador es estático
en vez de apoyarse en Redis como el store-mapping de Uber.
"""

import json
import os
from typing import Optional

from src.kitchan.modules.integraciones.rappi.domain.ports import RappiStoreMappingPort


class EnvRappiStoreMappingAdapter(RappiStoreMappingPort):
    def __init__(self):
        raw = os.getenv("RAPPI_STORE_ID_MAP", "{}")
        try:
            self._mapa: dict[str, str] = json.loads(raw)
        except json.JSONDecodeError:
            print(f"⚠️ [RAPPI] RAPPI_STORE_ID_MAP no es JSON válido: {raw!r}")
            self._mapa = {}

    async def get_restaurante_id(self, store_id: str) -> Optional[str]:
        return self._mapa.get(store_id)
