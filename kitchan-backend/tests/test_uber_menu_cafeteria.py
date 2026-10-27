"""El menú que se sube a Uber debe ser consistente: ids únicos, categorías que
solo referencian platillos existentes y combos más baratos que sus partes."""

from src.kitchan.modules.integraciones.uber.infrastructure.menu_cafeteria import (
    construir_menu_payload,
)


def _precios(menu: dict) -> dict:
    return {item["id"]: item["price_info"]["price"] for item in menu["items"]}


def test_ids_unicos_y_categorias_validas():
    menu = construir_menu_payload()
    ids = [item["id"] for item in menu["items"]]
    assert len(ids) == len(set(ids))

    for categoria in menu["categories"]:
        for entidad in categoria["entities"]:
            assert entidad["id"] in ids

    ids_categorias = {categoria["id"] for categoria in menu["categories"]}
    assert set(menu["menus"][0]["category_ids"]) == ids_categorias


def test_precios_en_centavos_enteros_y_con_descripcion():
    menu = construir_menu_payload()
    for item in menu["items"]:
        assert isinstance(item["price_info"]["price"], int)
        assert item["price_info"]["price"] > 0
        assert item["description"]["translations"]["es"]


def test_combos_cuestan_menos_que_la_suma_de_sus_partes():
    precios = _precios(construir_menu_payload())

    assert precios["item-combo-desayuno"] < (
        precios["item-croissant-jamon-queso"]
        + precios["item-cafe-americano"]
        + precios["item-jugo-naranja"]
    )
    assert precios["item-combo-pancakes-cafe"] < (
        precios["item-pancakes-frutos-rojos"] + precios["item-cappuccino"]
    )
    assert precios["item-combo-brunch-pareja"] < (
        precios["item-huevos-benedictinos"]
        + precios["item-waffle-helado"]
        + 2 * precios["item-cappuccino"]
    )
    assert precios["item-promo-mananera"] < (
        precios["item-croissant-jamon-queso"] + precios["item-cappuccino"]
    )
