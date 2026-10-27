"""Menú de la cafetería que KITCHAN publica en Uber Eats.

Como KITCHAN es el POS de la tienda, el menú se sube por API y cada PUT
reemplaza el menú completo: para agregar o quitar platillos se edita
CATEGORIAS y se vuelve a llamar a /menu/upload.

Los precios van en centavos (650 = $6.50). La API de menús de Uber no tiene
un campo de descuento: los combos y promos son platillos con un precio menor
a la suma de sus partes, y el ahorro se indica en la descripción.
"""

DIAS_SEMANA = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Disponible todo el día para que la demo funcione a cualquier hora. Para
# limitar desayuno/brunch por horario basta cambiar estos valores.
HORA_INICIO = "00:00"
HORA_FIN = "23:59"


def _platillo(id_item: str, titulo: str, descripcion: str, precio: int) -> dict:
    return {
        "id": id_item,
        "titulo": titulo,
        "descripcion": descripcion,
        "precio": precio,
    }


CATEGORIAS = [
    {
        "id": "cat-desayunos",
        "titulo": "Desayunos",
        "items": [
            _platillo(
                "item-tostada-aguacate",
                "Tostada de Aguacate y Huevo Pochado",
                "Pan de masa madre tostado, aguacate, huevo pochado, "
                "semillas de sésamo y un toque de limón.",
                650,
            ),
            _platillo(
                "item-tortilla-jamon-queso",
                "Tortilla de Huevos con Jamón y Queso",
                "Tortilla de tres huevos rellena de jamón y queso mozzarella, "
                "con tostadas y mantequilla.",
                550,
            ),
            _platillo(
                "item-pancakes-frutos-rojos",
                "Pancakes con Frutos Rojos y Miel",
                "Torre de tres pancakes esponjosos con frutillas, moras, "
                "miel de abeja y mantequilla.",
                700,
            ),
            _platillo(
                "item-croissant-jamon-queso",
                "Croissant de Jamón y Queso",
                "Croissant de mantequilla horneado al momento, relleno de "
                "jamón de pavo y queso gouda.",
                450,
            ),
            _platillo(
                "item-bowl-yogurt",
                "Bowl de Yogurt, Granola y Frutas",
                "Yogurt natural, granola crocante, plátano, fresas y un hilo de miel.",
                500,
            ),
        ],
    },
    {
        "id": "cat-brunch",
        "titulo": "Brunch",
        "items": [
            _platillo(
                "item-huevos-benedictinos",
                "Huevos Benedictinos",
                "Dos huevos pochados sobre pan inglés con jamón y salsa holandesa.",
                850,
            ),
            _platillo(
                "item-club-pollo",
                "Sándwich Club de Pollo",
                "Pechuga de pollo a la plancha, tocino, lechuga, tomate y "
                "mayonesa en pan tostado. Incluye papas.",
                800,
            ),
            _platillo(
                "item-waffle-helado",
                "Waffle con Helado de Vainilla y Maple",
                "Waffle belga dorado con una bola de helado de vainilla y "
                "sirope de maple.",
                750,
            ),
            _platillo(
                "item-bagel-salmon",
                "Bagel de Salmón y Queso Crema",
                "Bagel tostado con queso crema, salmón ahumado, alcaparras y "
                "cebolla morada.",
                950,
            ),
            _platillo(
                "item-ensalada-caesar",
                "Ensalada Caesar con Pollo",
                "Lechuga romana, pollo grillado, crutones, parmesano y "
                "aderezo Caesar casero.",
                800,
            ),
        ],
    },
    {
        "id": "cat-bebidas",
        "titulo": "Bebidas",
        "items": [
            _platillo(
                "item-cafe-americano",
                "Café Americano",
                "Café de origen ecuatoriano, filtrado, 12 oz.",
                200,
            ),
            _platillo(
                "item-cappuccino",
                "Cappuccino",
                "Espresso doble con leche texturizada y espuma cremosa, 12 oz.",
                300,
            ),
            _platillo(
                "item-jugo-naranja",
                "Jugo Natural de Naranja",
                "Naranja recién exprimida, sin azúcar añadida, 12 oz.",
                300,
            ),
        ],
    },
    {
        "id": "cat-combos",
        "titulo": "Combos y Promos",
        "items": [
            _platillo(
                "item-combo-desayuno",
                "Combo Desayuno: Croissant + Café + Jugo",
                "Croissant de jamón y queso, café americano y jugo natural "
                "de naranja. Ahorras $1.50.",
                800,
            ),
            _platillo(
                "item-combo-pancakes-cafe",
                "Combo Pancakes + Cappuccino",
                "Pancakes con frutos rojos y miel más un cappuccino. " "Ahorras $1.50.",
                850,
            ),
            _platillo(
                "item-combo-brunch-pareja",
                "Combo Brunch para Dos",
                "Huevos benedictinos, waffle con helado y dos cappuccinos. "
                "Ahorras $3.50.",
                1850,
            ),
            _platillo(
                "item-promo-mananera",
                "Promo Mañanera: Croissant + Cappuccino (-13%)",
                "Croissant de jamón y queso con un cappuccino a precio "
                "especial. Ahorras $1.00.",
                650,
            ),
        ],
    },
    {
        "id": "cat-principales",
        "titulo": "Platos Principales",
        "items": [
            _platillo(
                "item-hamburguesa-1",
                "Hamburguesa Kitchan",
                "Hamburguesa de carne de res con queso, lechuga y tomate.",
                1000,
            ),
        ],
    },
]


def _traduccion(texto: str) -> dict:
    return {"translations": {"es": texto}}


def construir_menu_payload() -> dict:
    """Arma el cuerpo del PUT /v2/eats/stores/{store_id}/menus."""
    items = []
    categorias = []

    for categoria in CATEGORIAS:
        for platillo in categoria["items"]:
            items.append(
                {
                    "id": platillo["id"],
                    "title": _traduccion(platillo["titulo"]),
                    "description": _traduccion(platillo["descripcion"]),
                    "price_info": {"price": platillo["precio"], "overrides": []},
                    "tax_info": {"tax_rate": 0},
                }
            )
        categorias.append(
            {
                "id": categoria["id"],
                "title": _traduccion(categoria["titulo"]),
                "entities": [
                    {"id": platillo["id"], "type": "ITEM"}
                    for platillo in categoria["items"]
                ],
            }
        )

    disponibilidad = [
        {
            "day_of_week": dia,
            "time_periods": [{"start_time": HORA_INICIO, "end_time": HORA_FIN}],
        }
        for dia in DIAS_SEMANA
    ]

    return {
        "items": items,
        "categories": categorias,
        "menus": [
            {
                "id": "menu-principal",
                "title": _traduccion("Menú Principal"),
                "category_ids": [categoria["id"] for categoria in CATEGORIAS],
                "service_availability": disponibilidad,
            }
        ],
        "modifier_groups": [],
    }
