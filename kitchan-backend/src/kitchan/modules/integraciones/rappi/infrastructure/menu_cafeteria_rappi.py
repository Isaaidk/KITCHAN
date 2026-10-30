"""Menú de la cafetería para Rappi.

Reutiliza el mismo catálogo (CATEGORIAS) que se publica en Uber Eats, para
que ambos canales ofrezcan lo mismo. Hoy ese catálogo vive en el módulo de
Uber; cuando exista un módulo de catálogo propio, solo cambia este import.
"""

import os

from src.kitchan.modules.integraciones.rappi.application.menu_rappi import (
    construir_menu_rappi,
    validar_menu_rappi,
)
from src.kitchan.modules.integraciones.uber.infrastructure.menu_cafeteria import (
    CATEGORIAS,
)

# Rappi exige enviar el menú a la tienda padre; la hija lo hereda.
TIENDA_PADRE_POR_DEFECTO = "900175767"


def tienda_padre_id() -> str:
    return (os.getenv("RAPPI_TIENDA_PADRE_ID") or TIENDA_PADRE_POR_DEFECTO).strip()


def precios_en_centavos() -> bool:
    """Por defecto se envían dólares con decimales (6.5): el simulador del
    sandbox de Rappi mostró el entero 650 como "$ 650", es decir, no lo trata
    como centavos. RAPPI_PRECIO_EN_CENTAVOS=true los envía como enteros."""
    return (os.getenv("RAPPI_PRECIO_EN_CENTAVOS") or "false").strip().lower() == "true"


def menu_de_cafeteria() -> dict:
    """Cuerpo del menú de la cafetería para la tienda padre de Rappi."""
    menu = construir_menu_rappi(
        CATEGORIAS, store_id=tienda_padre_id(), en_centavos=precios_en_centavos()
    )
    problemas = validar_menu_rappi(menu)
    if problemas:
        raise ValueError("El menú de Rappi no es válido: " + " | ".join(problemas))
    return menu
