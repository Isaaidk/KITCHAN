# Simulador de PedidosYa

Permite probar la integración PedidosYa (Delivery Hero Integration Middleware) sin la tienda de prueba real.

- `simular_pedidosya.py`: hace del Middleware y envía "Dispatch Order" con un JWT HS512 (`service: middleware`).
- `api_pedidosya_falsa.py`: hace del Integration Middleware y recibe las llamadas de KITCHAN (status y prepared) con Basic Auth.

> Qué NO prueba: el schema real del payload (los campos de `domain/models.py` son
> best-effort) ni las rutas reales del Middleware. Eso se confirma con la tienda de prueba.

## 1. Variables del `.env` (en `kitchan-backend/`, solo local)

```
PEDIDOSYA_JWT_SECRET=<secreto aleatorio>
PEDIDOSYA_PLUGIN_USERNAME=simulador
PEDIDOSYA_PLUGIN_PASSWORD=<aleatorio>
PEDIDOSYA_API_BASE=http://127.0.0.1:8011
PEDIDOSYA_REMOTE_ID_MAP={"KITCHAN-PYA-TEST-1": "<UUID del restaurante en KITCHAN>"}
```

## 2. Levantar (desde `kitchan-backend/`)

```
uvicorn scripts.simulador_pedidosya.api_pedidosya_falsa:app --port 8011
uvicorn src.kitchan.main:app --host 127.0.0.1 --port 8000
python scripts/simulador_pedidosya/simular_pedidosya.py nuevo-pedido
```

## 3. Flujo de prueba

| Paso | Cómo | Resultado esperado |
|---|---|---|
| Nuevo pedido | `simular_pedidosya.py nuevo-pedido` | 200 `ACKNOWLEDGED`, pedido NUEVA con total 18.75 |
| Reenvío duplicado | `nuevo-pedido --order-id <id ya usado>` | 200, sin duplicar |
| JWT falso | `simular_pedidosya.py jwt-invalido` | 401, no se crea nada |
| Aceptar | `POST /api/v1/integraciones/pedidosya/orders/{id}/accept` | EN_PREPARACION; el Middleware falso recibe `CONFIRMED` |
| Listo | `POST .../orders/{id}/ready` | LISTA; el Middleware falso recibe `PREPARED` |
| Rechazar | `POST .../orders/{id}/deny` con `{"reason": "..."}` | CANCELADA; recibe `REJECTED` + reason |
| Cancelar | `POST .../orders/{id}/cancel` con `{"reason": "..."}` | CANCELADA; recibe `CANCELLED` + reason |
