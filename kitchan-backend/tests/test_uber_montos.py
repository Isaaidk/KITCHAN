"""Uber Eats manda los montos en centavos ({"amount": 1000} = $10.00); el
mapeo del webhook debe convertirlos a unidades de moneda antes de crear el
pedido en KITCHAN."""

import pytest

from src.kitchan.modules.integraciones.uber.application.webhook_use_cases import (
    UberWebhookUseCase,
    _centavos_a_unidades,
)
from src.kitchan.modules.integraciones.uber.domain.models import UberWebhookPayload


def test_centavos_a_unidades():
    assert _centavos_a_unidades({"amount": 1000, "currency_code": "USD"}) == 10.0
    assert _centavos_a_unidades({"amount": 175}) == 1.75
    assert _centavos_a_unidades(1250) == 12.5
    assert _centavos_a_unidades({}) == 0.0
    assert _centavos_a_unidades({"amount": "no-numero"}) == 0.0


class _Tokens:
    async def get_restaurante_id_by_store(self, store_id):
        return "rest-1"

    async def get_app_token(self, restaurante_id):
        return "token"


class _UberApi:
    async def get_order_details(self, order_id, token):
        return {
            "eater": {"first_name": "Ana", "last_name": "T."},
            "payment": {"charges": {"total": {"amount": 1175}}},
            "cart": {
                "items": [
                    {
                        "title": "Hamburguesa Kitchan",
                        "quantity": 1,
                        "price": {"unit_price": {"amount": 1000}},
                    },
                    {
                        "title": "Coca-Cola 500 ml",
                        "quantity": 1,
                        "price": {"unit_price": {"amount": 175}},
                    },
                ]
            },
        }


class _Dispatcher:
    def __init__(self):
        self.orden = None

    async def dispatch_new_order(self, orden):
        self.orden = orden
        return "id-interno"


@pytest.mark.asyncio
async def test_webhook_convierte_centavos_a_unidades():
    dispatcher = _Dispatcher()
    use_case = UberWebhookUseCase(
        token_cache=_Tokens(), uber_api=_UberApi(), order_dispatcher=dispatcher
    )
    payload = UberWebhookPayload(
        event_id="e1",
        event_type="orders.notification",
        meta={"resource_id": "orden-1", "user_id": "store-1"},
    )

    await use_case.process_notification(payload)

    assert dispatcher.orden.total == 11.75
    assert [i.precio_unitario for i in dispatcher.orden.items] == [10.0, 1.75]
