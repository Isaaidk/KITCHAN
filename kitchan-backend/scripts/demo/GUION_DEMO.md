# Guion de la demo de KITCHAN

Duración sugerida: **8–10 minutos**.

## Antes de la presentación (el día anterior)

1. Haz un ensayo completo con este guion.
2. Revisa que existan `kitchan-backend/.env` (con el bloque de Rappi y PedidosYa de prueba) y el `venv` del backend.
3. Ten a mano las **evidencias**: captura del ticket de Rappi `INB-20260930-9253`, los correos con Rappi y PedidosYa, el rechazo de PedidosYa y la confirmación del formulario de integradores.

## Arranque (5 minutos antes)

1. Doble clic en `kitchan-backend/scripts/demo/iniciar_demo.cmd`.
   Abre Docker, las APIs falsas, el backend, el frontend, el navegador y la ventana **"KITCHAN - Menu de la demo"**.
2. Inicia sesión en KITCHAN con el usuario administrador.
3. Deja lado a lado el **navegador (KDS)** y la ventana del **menú de la demo**.
4. Si en la cola quedaron pedidos de ensayos anteriores, márcalos como **Entregado** para empezar con el tablero limpio (los que siguen en *Nueva* o *En preparación* se cancelan solos a los 20 minutos).

## Demo paso a paso

| # | Qué haces | Qué se ve | Qué dices |
|---|---|---|---|
| 1 | Muestras **Integraciones** | Uber conectado; Rappi y PedidosYa disponibles | "KITCHAN centraliza los pedidos de tres plataformas. Uber está conectado a su sandbox real; Rappi y PedidosYa usan simuladores mientras las plataformas aprueban nuestras credenciales." |
| 2 | Menú → **1** (pedido de Rappi) | La tarjeta aparece sola en *Nueva*, con aviso | "El pedido llega por webhook firmado, igual que lo envía Rappi, y aparece en tiempo real sin recargar." |
| 3 | Menú → **2** (pedido de PedidosYa) | Segunda tarjeta, con el color de PedidosYa | "PedidosYa usa otro protocolo, un JWT del Integration Middleware. El núcleo de KITCHAN no cambia: cada plataforma es un adaptador." |
| 4 | Menú → **3** (intentos falsos) | No aparece nada nuevo | "Si alguien intenta enviar un pedido falso, se rechaza por firma o token inválido." |
| 5 | En el KDS: **Aceptar** el pedido de Rappi y luego **Listo** | Pasa a *En preparación* y a *Lista* | "La cocina acepta y marca listo; KITCHAN avisa a la plataforma en cada paso." |
| 6 | Abres el detalle de un pedido | Línea de tiempo, productos y notas | "El detalle muestra el estado y lo que pidió el cliente." |
| 7 | Menú → **1** y luego **4** (el cliente cancela) | La tarjeta se cancela con aviso rojo | "Si el cliente cancela desde la app de Rappi, KITCHAN lo refleja al instante." |
| 8 | **Cancelar** el pedido de PedidosYa con un motivo | Se cancela y avisa a la plataforma | "Cada plataforma tiene sus propios motivos de rechazo y KITCHAN usa los correctos." |
| 9 | **Analíticas** | Pedidos del día por canal | "Las métricas del día se calculan por canal." |

## Cierre (1 minuto)

> "Lo que dependía de nosotros, desarrollar y probar las integraciones, está terminado. Uber funciona contra su sandbox real. Rappi y PedidosYa exigen una autorización comercial que ya gestionamos y documentamos; cuando llegue, se conectan cambiando solo la configuración, sin tocar el código."

## Si algo falla

- **No aparecen pedidos:** revisa que la ventana "KITCHAN - Backend" no muestre errores y que el menú no diga "KITCHAN no responde".
- **El KDS dice "Reconectando":** recarga la página.
- **Docker no arranca:** abre Docker Desktop a mano y vuelve a ejecutar `iniciar_demo.cmd`.

## Al terminar

Doble clic en `detener_demo.cmd`: cierra solo los procesos de la demo (no toca el navegador ni otras terminales) y detiene Postgres y Redis (sin borrar datos).
