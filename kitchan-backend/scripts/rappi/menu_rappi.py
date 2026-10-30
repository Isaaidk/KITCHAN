"""Menú de Rappi: vista previa y envío a la tienda padre del sandbox.

Uso (desde kitchan-backend/):
    python scripts/rappi/menu_rappi.py --vista-previa   # valida y guarda el JSON
    python scripts/rappi/menu_rappi.py --subir          # lo envía a Rappi

La vista previa no usa la red: arma el menú de la cafetería, aplica las reglas
de Rappi y escribe `menu_rappi_vista_previa.json` para revisarlo (también se
puede cargar en la herramienta Menú del Integrations Manager). Para enviar
hace falta el .env con las credenciales de Rappi.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
load_dotenv(RAIZ / ".env")

from src.kitchan.modules.integraciones.rappi.infrastructure.menu_cafeteria_rappi import (  # noqa: E402
    menu_de_cafeteria,
    precios_en_centavos,
)


def vista_previa() -> dict:
    menu = menu_de_cafeteria()  # valida; lanza ValueError si no cumple las reglas
    destino = RAIZ / "menu_rappi_vista_previa.json"
    destino.write_text(json.dumps(menu, ensure_ascii=False, indent=2), encoding="utf-8")
    categorias = {item["category"]["name"] for item in menu["items"]}
    print(f"✅ Menú válido para la tienda padre {menu['storeId']}")
    print(f"   {len(menu['items'])} productos en {len(categorias)} categorías")
    unidad = "centavos" if precios_en_centavos() else "dólares"
    print(f"   Precios enviados en {unidad} (RAPPI_PRECIO_EN_CENTAVOS)")
    print(f"   Vista previa guardada en {destino}")
    return menu


async def subir(menu: dict) -> None:
    from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.http_order_adapter import (
        RappiHttpAdapter,
    )
    from src.kitchan.modules.integraciones.rappi.infrastructure.adapters.redis_token_adapter import (
        RedisRappiTokenAdapter,
    )

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    adaptador = RappiHttpAdapter(RedisRappiTokenAdapter(redis_url))
    await adaptador.upload_menu(menu)
    print("✅ Rappi aceptó el menú. Queda pendiente su aprobación (MENU_APPROVED).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--vista-previa", action="store_true")
    grupo.add_argument("--subir", action="store_true")
    args = parser.parse_args()

    menu = vista_previa()
    if args.subir:
        asyncio.run(subir(menu))


if __name__ == "__main__":
    main()
