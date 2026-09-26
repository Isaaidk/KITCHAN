# Simulador de Rappi

Permite probar la integración Rappi de KITCHAN sin acceso al ambiente DEV de Rappi.

- `simular_rappi.py`: hace de Rappi enviando webhooks firmados (`Rappi-Signature`) a KITCHAN.
- `api_rappi_falsa.py`: hace de la API de Rappi y recibe las llamadas de KITCHAN al aceptar, rechazar o marcar listo.

> Qué NO prueba: que Rappi acepte las credenciales reales ni que el formato del
> payload sea idéntico al real. Eso se confirma con acceso DEV.

## 1. Configurar el `.env` (en `kitchan-backend/`, solo local)

Copia tu `.env` del backend principal y agrega o cambia estas variables:

```
RAPPI_WEBHOOK_SECRET=secreto-local-simulador
RAPPI_CLIENT_ID=simulador
RAPPI_CLIENT_SECRET=simulador
RAPPI_AUTH_BASE=http://127.0.0.1:8010
RAPPI_API_BASE=http://127.0.0.1:8010
RAPPI_STORE_ID_MAP={"900000001": "<UUID del restaurante en KITCHAN>"}
```

Son valores de prueba. Cuando Rappi entregue las credenciales reales, reemplázalos y
vuelve a poner las URLs de DEV (`https://api.dev.rappi.com`, etc.).

## 2. Levantar todo (3 terminales, desde `kitchan-backend/`)

```
# Terminal 1: API de Rappi falsa
uvicorn scripts.simulador_rappi.api_rappi_falsa:app --port 8010

# Terminal 2: backend de KITCHAN (de ESTA carpeta, rama feature/Integracion/Rappi)
uvicorn src.kitchan.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir src

# Terminal 3: enviar eventos
python scripts/simulador_rappi/simular_rappi.py nuevo-pedido
```

## 3. Flujo de prueba

| Paso | Cómo | Resultado esperado |
|---|---|---|
| Nuevo pedido | `simular_rappi.py nuevo-pedido` (imprime el `order_id`) | 200, pedido en KDS con total 18.75 |
| Aceptar | `/docs` → `POST /api/v1/integraciones/rappi/orders/{order_id}/accept` (con login) | EN_PREPARACION; la API falsa muestra `TAKE ... x-authorization OK` |
| Listo | `POST .../orders/{order_id}/ready` | LISTA; la API falsa muestra `READY_FOR_PICKUP` |
| Rechazar (otro pedido) | `POST .../orders/{order_id}/deny` | CANCELADA; la API falsa muestra `REJECT` y el body |
| Cancelación desde Rappi | `simular_rappi.py cancelar --order-id <id>` | 200, pedido CANCELADO (si no estaba LISTA/ENTREGADA) |
| Reenvío duplicado | `nuevo-pedido --order-id <id ya usado>` | 200, sin duplicar el pedido |
| Firma falsa | `simular_rappi.py firma-invalida` | 403, no se crea nada |

Si el token de Rappi quedó cacheado en Redis (`rappi_app_token`) de otra prueba,
bórralo con `redis-cli DEL rappi_app_token`.
