"""Tests del menú de Rappi: armado desde el catálogo y validación de las
reglas que Rappi rechaza. No usan la red.
"""

import pytest

from src.kitchan.modules.integraciones.rappi.application.menu_rappi import (
    construir_menu_rappi,
    validar_menu_rappi,
)
from src.kitchan.modules.integraciones.rappi.infrastructure.menu_cafeteria_rappi import (
    TIENDA_PADRE_POR_DEFECTO,
    menu_de_cafeteria,
)

CATALOGO = [
    {
        "id": "cat-a",
        "titulo": "Desayunos",
        "items": [
            {
                "id": "item-1",
                "titulo": "Tostada",
                "descripcion": "Pan y huevo",
                "precio": 650,
            },
            {
                "id": "item-2",
                "titulo": "Pancakes",
                "descripcion": "Con miel",
                "precio": 700,
            },
        ],
    },
    {
        "id": "cat-b",
        "titulo": "Bebidas",
        "items": [
            {
                "id": "item-3",
                "titulo": "Café",
                "descripcion": "Americano",
                "precio": 200,
            }
        ],
    },
]


def test_el_menu_lleva_la_tienda_y_un_producto_por_platillo():
    menu = construir_menu_rappi(CATALOGO, store_id="900175767")

    assert menu["storeId"] == "900175767"
    assert [i["sku"] for i in menu["items"]] == ["item-1", "item-2", "item-3"]
    assert all(i["type"] == "PRODUCT" and i["children"] == [] for i in menu["items"])


def test_cada_producto_lleva_su_categoria_y_posicion():
    menu = construir_menu_rappi(CATALOGO, store_id="1")
    tostada, pancakes, cafe = menu["items"]

    assert tostada["category"] == {
        "id": "cat-a",
        "name": "Desayunos",
        "maxQty": 0,
        "minQty": 0,
        "sortingPosition": 0,
    }
    assert (tostada["sortingPosition"], pancakes["sortingPosition"]) == (0, 1)
    assert cafe["category"]["sortingPosition"] == 1


def test_los_precios_van_en_centavos_o_en_dolares():
    en_centavos = construir_menu_rappi(CATALOGO, store_id="1", en_centavos=True)
    en_dolares = construir_menu_rappi(CATALOGO, store_id="1", en_centavos=False)

    assert en_centavos["items"][0]["price"] == 650
    assert en_dolares["items"][0]["price"] == 6.5


def test_un_menu_correcto_no_tiene_problemas():
    assert validar_menu_rappi(construir_menu_rappi(CATALOGO, store_id="1")) == []


def _con(cambio: dict) -> dict:
    menu = construir_menu_rappi(CATALOGO, store_id="1")
    menu["items"][0].update(cambio)
    return menu


@pytest.mark.parametrize(
    "menu,fragmento",
    [
        ({"storeId": "1", "items": []}, "Items is required"),
        ({"items": [{}]}, "storeId"),
        (_con({"sku": ""}), "sku no puede estar vacío"),
        (_con({"price": 0}), "precio debe ser > 0"),
        (_con({"name": "A"}), "al menos 2 caracteres"),
        (_con({"description": ""}), "descripción necesita"),
        (_con({"name": "Tostada 🍳"}), "emojis"),
        (_con({"type": "TOPPING"}), "debe ser PRODUCT"),
        (_con({"category": {"id": "", "name": "Desayunos"}}), "necesita id"),
    ],
)
def test_las_reglas_de_rappi_se_detectan(menu, fragmento):
    problemas = validar_menu_rappi(menu)

    assert any(fragmento in p for p in problemas), problemas


def test_un_sku_repetido_con_datos_distintos_se_rechaza():
    menu = construir_menu_rappi(CATALOGO, store_id="1")
    menu["items"][1]["sku"] = menu["items"][0]["sku"]

    assert any("se repite" in p for p in validar_menu_rappi(menu))


def test_el_menu_de_la_cafeteria_es_valido_y_va_a_la_tienda_padre(monkeypatch):
    monkeypatch.delenv("RAPPI_TIENDA_PADRE_ID", raising=False)
    monkeypatch.delenv("RAPPI_PRECIO_EN_CENTAVOS", raising=False)

    menu = menu_de_cafeteria()

    assert menu["storeId"] == TIENDA_PADRE_POR_DEFECTO == "900175767"
    # Por defecto el precio va en dólares (6.5), no en centavos (650).
    assert menu["items"][0]["price"] == 6.5
    assert len(menu["items"]) == 18
    assert len({i["sku"] for i in menu["items"]}) == 18
    assert validar_menu_rappi(menu) == []


def test_la_tienda_y_la_unidad_de_precio_se_configuran(monkeypatch):
    monkeypatch.setenv("RAPPI_TIENDA_PADRE_ID", "123")
    monkeypatch.setenv("RAPPI_PRECIO_EN_CENTAVOS", "true")

    menu = menu_de_cafeteria()

    assert menu["storeId"] == "123"
    assert menu["items"][0]["price"] == 650
