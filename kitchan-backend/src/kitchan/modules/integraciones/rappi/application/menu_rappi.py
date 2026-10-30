"""Menú de Rappi a partir de un catálogo neutro.

Arma el cuerpo de `POST .../restaurants-integrations-public-api/menu` según la
guía "Gestionar menús en tiendas" de Rappi y valida las reglas que Rappi
rechaza, para detectarlas antes de enviar el menú.

El catálogo es una lista de categorías, cada una con sus platillos:
    {"id": str, "titulo": str, "items": [{"id", "titulo", "descripcion",
    "precio"}]}   con el precio en CENTAVOS (650 = $6.50).

Reglas de Rappi que se cumplen o validan aquí:
- Con mapeo automático cada producto lleva `sku` (único, no vacío).
- Solo dos niveles (producto -> topping); este catálogo no usa toppings.
- Los precios van a precio completo, sin descuentos, y un producto sin
  toppings debe costar más de 0.
- Nombres y descripciones de al menos 2 caracteres, sin emojis.
- El menú se envía solo a la tienda PADRE; la hija lo hereda.
"""

import re
from typing import Any

# Emojis y símbolos pictográficos: Rappi no los admite en textos del menú.
_EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f2ff\U0000fe0f]"
)


def _precio(centavos: int, en_centavos: bool) -> int | float:
    """Rappi pide `price` como número. La moneda local de la documentación
    (COP) usa enteros; para USD no está confirmado si van centavos o dólares,
    por eso se puede cambiar con RAPPI_PRECIO_EN_CENTAVOS."""
    if en_centavos:
        return int(centavos)
    return round(centavos / 100, 2)


def construir_menu_rappi(
    categorias: list[dict[str, Any]],
    store_id: str,
    en_centavos: bool = True,
) -> dict[str, Any]:
    """Cuerpo del POST de menú para la tienda padre `store_id`."""
    productos: list[dict[str, Any]] = []
    for posicion_categoria, categoria in enumerate(categorias):
        info_categoria = {
            "id": categoria["id"],
            "name": categoria["titulo"],
            "maxQty": 0,
            "minQty": 0,
            "sortingPosition": posicion_categoria,
        }
        for posicion, platillo in enumerate(categoria["items"]):
            productos.append(
                {
                    "type": "PRODUCT",
                    "name": platillo["titulo"],
                    "description": platillo["descripcion"],
                    "price": _precio(platillo["precio"], en_centavos),
                    "sku": platillo["id"],
                    "sortingPosition": posicion,
                    "category": dict(info_categoria),
                    "children": [],
                }
            )
    return {"storeId": str(store_id), "items": productos}


def validar_menu_rappi(menu: dict[str, Any]) -> list[str]:
    """Lista de problemas que Rappi rechazaría (vacía si el menú es válido)."""
    problemas: list[str] = []
    items = menu.get("items") or []
    if not menu.get("storeId"):
        problemas.append("Falta storeId.")
    if not items:
        problemas.append("Items is required: el menú no tiene productos.")

    skus: dict[str, str] = {}
    for item in items:
        nombre = item.get("name") or ""
        sku = item.get("sku")
        referencia = nombre or sku or "(sin nombre)"

        if item.get("type") != "PRODUCT":
            problemas.append(f"{referencia}: el primer nivel debe ser PRODUCT.")
        if not sku:
            problemas.append(f"{referencia}: el sku no puede estar vacío.")
        elif sku in skus and skus[sku] != nombre:
            problemas.append(f"El sku '{sku}' se repite con atributos distintos.")
        skus[sku or ""] = nombre

        if len(nombre) < 2:
            problemas.append(f"{referencia}: el nombre necesita al menos 2 caracteres.")
        descripcion = item.get("description") or ""
        if len(descripcion) < 2:
            problemas.append(f"{referencia}: la descripción necesita 2 caracteres.")
        if _EMOJI.search(nombre) or _EMOJI.search(descripcion):
            problemas.append(f"{referencia}: los textos no pueden tener emojis.")

        if not item.get("children") and not (item.get("price") or 0) > 0:
            problemas.append(f"{referencia}: sin toppings, el precio debe ser > 0.")

        categoria = item.get("category") or {}
        if not categoria.get("id"):
            problemas.append(f"{referencia}: la categoría necesita id.")
        if len(categoria.get("name") or "") < 2:
            problemas.append(f"{referencia}: el nombre de la categoría es muy corto.")

        for hijo in item.get("children") or []:
            if hijo.get("type") != "TOPPING":
                problemas.append(f"{referencia}: los hijos deben ser TOPPING.")
            if hijo.get("children"):
                problemas.append(f"{referencia}: los toppings no pueden tener hijos.")
    return problemas
