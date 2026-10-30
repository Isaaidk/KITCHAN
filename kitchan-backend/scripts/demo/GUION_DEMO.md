# Guion de la demo de KITCHAN

Duración sugerida: **8–10 minutos**.

Canales de la demo: **Uber Eats** y **Rappi** (sus sandboxes reales) y **WhatsApp** (nuestro bot).

## Antes de la presentación (el día anterior)

1. Haz un ensayo completo con este guion.
2. Revisa que existan `kitchan-backend/.env` (con los bloques de Uber, Rappi y WhatsApp) y el `venv` del backend.
3. Comprueba que Rappi esté conectado (Integraciones → **Conectar Rappi**, con el usuario sandbox) y que el túnel de ngrok use el dominio registrado en Uber y en Rappi.
4. Ten a mano las **evidencias**: captura del ticket de Rappi `INB-20260930-9253`, los correos con Rappi y la confirmación del formulario de integradores.

## Arranque (5 minutos antes)

1. Doble clic en `kitchan-backend/scripts/demo/iniciar_demo.cmd`.
   Abre Docker, **aplica las migraciones de la base de datos**, levanta el backend, el frontend y ngrok, y abre el navegador.
   Si el script se detiene con "No se pudieron aplicar las migraciones", corre `alembic upgrade head` desde `kitchan-backend` y vuelve a intentarlo (sin ese paso el Dashboard, la cola y el historial fallan).
2. Inicia sesión en KITCHAN con el usuario administrador.
3. Ten a mano el celular con WhatsApp, el simulador de órdenes del portal de Rappi y la app de Uber Eats, junto al **navegador (KDS)**.
4. Si en la cola quedaron pedidos de ensayos anteriores, márcalos como **Entregado** para empezar con el tablero limpio (los que siguen en *Nueva* o *En preparación* se cancelan solos a los 20 minutos).

## Demo paso a paso

| # | Qué haces | Qué se ve | Qué dices |
|---|---|---|---|
| 1 | Muestras **Integraciones** | Uber, Rappi y WhatsApp conectados | "KITCHAN centraliza los pedidos de tres canales. Uber y Rappi están conectados a sus sandboxes reales; WhatsApp es nuestro propio bot." |
| 2 | Haces un pedido en **Uber Eats** (app o sandbox) | La tarjeta aparece sola en *Nueva*, con aviso | "El pedido llega por webhook firmado y aparece en tiempo real sin recargar." |
| 3 | Creas una orden en el **simulador de órdenes del portal de Rappi** (tienda Vangalia Dev1) | Segunda tarjeta, con el color de Rappi | "Rappi nos avisa por webhook firmado con HMAC. El núcleo de KITCHAN no cambia: cada plataforma es un adaptador." |
| 4 | Mandas un mensaje de **WhatsApp** al número del negocio y haces el pedido con el bot | Tercera tarjeta, en verde WhatsApp, con teléfono, tipo de entrega y dirección en el detalle | "Los clientes también piden por WhatsApp. Nuestro bot firma el pedido con un secreto compartido y KITCHAN le contesta cada decisión de la cocina." |
| 5 | En el KDS: **Aceptar** cada pedido y luego **Listo** | Pasa a *En preparación* y a *Lista* | "La cocina acepta y marca listo; KITCHAN avisa a la plataforma en cada paso. Con WhatsApp, además, el cliente recibe el aviso en su chat." |
| 6 | Abres el detalle de un pedido | Línea de tiempo, productos y notas | "El detalle muestra el estado y lo que pidió el cliente." |
| 7 | **Cancelar** un pedido nuevo con un motivo | Se cancela y avisa a la plataforma | "Cada plataforma tiene sus propios motivos de rechazo y KITCHAN usa los correctos." |
| 8 | **Dashboard** y luego **Analíticas** | Ventas, ticket promedio y tiempo de preparación; comparación de canales, platos más vendidos y horas pico | "El dashboard resume el día y las analíticas comparan canales, platos y horarios." |

## Cierre (1 minuto)

> "Lo que dependía de nosotros está terminado y probado. Uber y Rappi funcionan contra sus sandboxes reales: reciben pedidos por webhook firmado y KITCHAN responde con aceptar, rechazar y listo. WhatsApp es un servicio propio y su contrato es nuestro."

## Si algo falla

- **No aparecen pedidos:** revisa que la ventana "KITCHAN - Backend" no muestre errores . Para Rappi, mira en `http://127.0.0.1:4040` (ngrok) si el aviso llegó y con qué código respondió KITCHAN.
- **El KDS dice "Reconectando":** recarga la página.
- **Docker no arranca:** abre Docker Desktop a mano y vuelve a ejecutar `iniciar_demo.cmd`.

## Al terminar

Doble clic en `detener_demo.cmd`: cierra solo los procesos de la demo (no toca el navegador ni otras terminales) y detiene Postgres y Redis (sin borrar datos).
