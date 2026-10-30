# Guion de la demo de KITCHAN

Duración sugerida: **8–10 minutos**.

## Antes de la presentación (el día anterior)

1. Haz un ensayo completo con este guion.
2. Revisa que existan `kitchan-backend/.env` (con el bloque de Rappi y PedidosYa de prueba) y el `venv` del backend.
3. Ten a mano las **evidencias**: captura del ticket de Rappi `INB-20260930-9253`, los correos con Rappi y PedidosYa, el rechazo de PedidosYa y la confirmación del formulario de integradores.

## Arranque (5 minutos antes)

1. Doble clic en `kitchan-backend/scripts/demo/iniciar_demo.cmd`.
   Abre Docker, **aplica las migraciones de la base de datos**, levanta las APIs falsas, el backend y el frontend, y abre el navegador y la ventana **"KITCHAN - Menu de la demo"**.
   Si el script se detiene con "No se pudieron aplicar las migraciones", corre `alembic upgrade head` desde `kitchan-backend` y vuelve a intentarlo (sin ese paso el Dashboard, la cola y el historial fallan).
2. Inicia sesión en KITCHAN con el usuario administrador.
3. Deja lado a lado el **navegador (KDS)** y la ventana del **menú de la demo**.
4. Si en la cola quedaron pedidos de ensayos anteriores, márcalos como **Entregado** para empezar con el tablero limpio (los que siguen en *Nueva* o *En preparación* se cancelan solos a los 20 minutos).

## Demo paso a paso

| # | Qué haces | Qué se ve | Qué dices |
|---|---|---|---|
| 1 | Muestras **Integraciones** | Uber conectado; Rappi, PedidosYa y WhatsApp disponibles | "KITCHAN centraliza los pedidos de cuatro canales. Uber está conectado a su sandbox real. Rappi ya tiene su sandbox (login y menú reales). WhatsApp es nuestro propio bot. En la demo, Rappi, PedidosYa y WhatsApp usan simuladores y se identifican como tales." |
| 2 | Menú → **1** (pedido de Rappi) | La tarjeta aparece sola en *Nueva*, con aviso | "El pedido llega por webhook firmado, igual que lo envía Rappi, y aparece en tiempo real sin recargar." |
| 3 | Menú → **2** (pedido de PedidosYa) | Segunda tarjeta, con el color de PedidosYa | "PedidosYa usa otro protocolo, un JWT del Integration Middleware. El núcleo de KITCHAN no cambia: cada plataforma es un adaptador." |
| 4 | Menú → **7** (pedido de WhatsApp) | Tercera tarjeta, en verde WhatsApp, con teléfono, tipo de entrega y dirección en el detalle | "Los clientes también piden por WhatsApp. Nuestro bot firma el pedido con un secreto compartido y KITCHAN le contesta cada decisión de la cocina." |
| 5 | Menú → **3** (intentos falsos) | No aparece nada nuevo | "Si alguien intenta enviar un pedido falso, se rechaza por firma o token inválido, en los tres canales." |
| 6 | En el KDS: **Aceptar** el pedido de Rappi (y el de WhatsApp) y luego **Listo** | Pasa a *En preparación* y a *Lista* | "La cocina acepta y marca listo; KITCHAN avisa a la plataforma en cada paso. Con WhatsApp, además, se ve en la ventana del bot el mensaje que le llegaría al cliente." |
| 7 | Abres el detalle de un pedido | Línea de tiempo, productos y notas | "El detalle muestra el estado y lo que pidió el cliente." |
| 8 | Menú → **1** y luego **4** (el cliente cancela) | La tarjeta se cancela con aviso rojo | "Si el cliente cancela desde la app de Rappi, KITCHAN lo refleja al instante." |
| 9 | **Cancelar** el pedido de PedidosYa con un motivo | Se cancela y avisa a la plataforma | "Cada plataforma tiene sus propios motivos de rechazo y KITCHAN usa los correctos." |
| 10 | **Dashboard** y luego **Analíticas** | Ventas, ticket promedio y tiempo de preparación; comparación de canales, platos más vendidos y horas pico | "El dashboard resume el día y las analíticas comparan canales, platos y horarios." |

## Cierre (1 minuto)

> "Lo que dependía de nosotros está terminado y probado. Uber funciona contra su sandbox real. Rappi ya nos entregó su sandbox: el login y el menú son reales, y falta la ruta de su API v2 y el secreto de firma para recibir pedidos reales. WhatsApp es un servicio propio y su contrato es nuestro. PedidosYa espera la aprobación de su Account Manager. En la demo, los canales que aún no tienen pedidos reales usan simuladores."

## Si algo falla

- **No aparecen pedidos:** revisa que la ventana "KITCHAN - Backend" no muestre errores y que el menú no diga "KITCHAN no responde".
- **El KDS dice "Reconectando":** recarga la página.
- **Docker no arranca:** abre Docker Desktop a mano y vuelve a ejecutar `iniciar_demo.cmd`.

## Al terminar

Doble clic en `detener_demo.cmd`: cierra solo los procesos de la demo (no toca el navegador ni otras terminales) y detiene Postgres y Redis (sin borrar datos).
