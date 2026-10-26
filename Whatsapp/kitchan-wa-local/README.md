# KITCHAN WhatsApp Local — FastAPI + Cloud API

Proyecto local para recibir webhooks de WhatsApp Cloud API, guardar mensajes/eventos en SQLite, verlos en una bandeja web, enviar mensajes manualmente y responder automáticamente a mensajes de texto.

## 1. Requisitos
- Python 3.11 o superior recomendado.
- Aplicación Meta con WhatsApp configurado y un número habilitado para Cloud API.
- Token con permiso `whatsapp_business_messaging`; para administrar suscripciones, también el permiso apropiado de administración.
- `Phone Number ID`, `App Secret`, `WABA ID` (para comprobar la suscripción) y una versión vigente de Graph API que esté disponible en tu aplicación.

## 2. Instalar y arrancar (Windows PowerShell)

```powershell
cd kitchan-whatsapp-local
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edita .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Abre http://127.0.0.1:8000 para la bandeja. Swagger: http://127.0.0.1:8000/docs. Salud: http://127.0.0.1:8000/health.

## 3. Completar `.env`
- `WHATSAPP_ACCESS_TOKEN`: token válido de Meta. No lo publiques ni lo subas a Git.
- `WHATSAPP_PHONE_NUMBER_ID`: ID técnico del número.
- `WHATSAPP_API_VERSION`: una versión activa de Graph API, por ejemplo el formato `vNN.0` que muestre Meta para tu app. No uses `vXX.X` literalmente.
- `WHATSAPP_VERIFY_TOKEN`: secreto aleatorio que inventas tú y que debe coincidir con el configurado en Webhooks.
- `WHATSAPP_APP_SECRET`: App Secret de Meta App Dashboard > Settings > Basic. Se usa para validar firmas de POST.

Reinicia Uvicorn después de cambiar variables de `.env`.

## 4. Exponer el servidor local a Meta
Meta no puede llamar a `127.0.0.1`: el webhook necesita una URL pública HTTPS.

**Windows (recomendado, un solo comando):**

```powershell
cd kitchan-wa-local
.\scripts\start-public.ps1
```

El script levanta Uvicorn, abre el túnel y muestra la **Webhook URL** para Meta. La URL también queda en `data/public-url.txt`. Para apagar todo:

```powershell
.\scripts\stop-public.ps1
```

**Importante:** cada vez que apagas el túnel, la URL `*.trycloudflare.com` **deja de existir**. Al volver a ejecutar `start-public.ps1` obtienes una URL **nueva**; debes actualizarla en Meta Developers.

En Meta Developers, WhatsApp > Configuration/Webhooks:

- Callback URL: la URL que imprime el script (termina en `/webhook`)
- Verify token: el valor exacto de `WHATSAPP_VERIFY_TOKEN`
- Suscribe el campo `messages`.

**Alternativa:** [ngrok](https://ngrok.com/) (`ngrok http 8000`) si prefieres dominio fijo con cuenta de pago.

La verificación GET devuelve `hub.challenge`. Los POST solo se procesan si `X-Hub-Signature-256` es válido con el App Secret.

## 5. Suscribir la app a la WABA
La configuración de webhook en la app y la suscripción de la aplicación a la cuenta WABA son pasos distintos. Si no llegan eventos aunque el callback esté verificado, comprueba en Meta que la app está suscrita a la WABA. La API oficial usa `POST /{WABA_ID}/subscribed_apps` con token y permisos adecuados. No registres ni desregistres el teléfono para hacer esta comprobación.

## 6. Prueba
1. Comprueba `/health` y abre la bandeja local.
2. Desde un número distinto, envía un mensaje al número empresarial conectado a Cloud API.
3. Revisa la terminal: debe aparecer `Mensaje entrante`.
4. El mensaje aparece en la bandeja SQLite y, si está activado, se envía la respuesta automática configurada.
5. Pulsa un mensaje entrante para rellenar el teléfono en el formulario de respuesta manual.

El envío solo será aceptado si el número está correctamente habilitado en Cloud API y el destinatario cumple las reglas de Meta. Dentro de la ventana de atención iniciada por el usuario puedes responder con texto libre; fuera de la ventana de 24 horas normalmente necesitas una plantilla aprobada. Para números de prueba, el destinatario debe estar autorizado en la configuración de Meta.

## 7. Qué guarda
SQLite se crea automáticamente en `data/whatsapp.db`. Guarda mensajes entrantes, mensajes salientes enviados por este panel y eventos de estado. Es una herramienta de desarrollo, no una base de datos de producción.

## Limitaciones importantes
- El webhook recibe eventos nuevos después de configurarlo y suscribirse; no descarga automáticamente conversaciones antiguas del teléfono.
- La app procesa textos y guarda indicadores de imágenes, audios, documentos, vídeos y stickers; no descarga ni transcribe los medios todavía.
- La respuesta automática se aplica solo a mensajes entrantes de texto, para evitar respuestas inadecuadas a archivos o botones.
- Esta interfaz no tiene login ni control de acceso. Úsala solo en tu máquina local; no expongas el panel completo a Internet. El túnel público debe apuntar al backend para que Meta llegue al webhook, pero no publiques el dashboard como servicio abierto.
- La base de datos y los logs pueden contener información personal. Protege el equipo y no compartas `data/whatsapp.db`.
- Para producción añade autenticación, colas persistentes, reintentos, política de privacidad, controles de acceso, métricas y almacenamiento seguro de secretos.

## Solución de problemas
- `403` al verificar: `WHATSAPP_VERIFY_TOKEN` no coincide.
- `401` al POST: `WHATSAPP_APP_SECRET` incorrecto o firma ausente.
- No llegan mensajes: verifica HTTPS público, suscripción `messages`, suscripción de la app a la WABA y que escribes al número correcto.
- Error al enviar: abre el detalle de error de Meta; revisa token vencido/permisos, Phone Number ID, versión Graph API, formato del teléfono y ventana/plantilla.
- No llega respuesta automática: confirma el interruptor en la bandeja y que el mensaje entrante sea texto.

## 8. Integración con KITCHAN (pedidos)
El bot sigue siendo un servicio independiente (puerto **8001**; el backend de KITCHAN usa el 8000). Solo habla con KITCHAN por HTTP firmado:

1. El cliente confirma el pedido por WhatsApp → el bot lo guarda y hace `POST {KITCHAN_API_URL}/api/v1/integraciones/whatsapp/webhook/new-order`.
2. En KITCHAN el pedido aparece como canal **WhatsApp** en la cola; el restaurante lo acepta, rechaza o marca listo.
3. KITCHAN llama a `POST /api/kitchan/orders/{id}/status` del bot y el bot avisa al cliente por WhatsApp (en un rechazo/cancelación también devuelve el stock a la hoja).

Variables (`.env`): `KITCHAN_API_URL`, `KITCHAN_BOT_SECRET` (igual a `WHATSAPP_BOT_SECRET` del backend) y `KITCHAN_STORE_ID` (clave en `WHATSAPP_STORE_ID_MAP` del backend → `restaurante_id`). Las firmas HMAC-SHA256 (`X-Kitchan-Signature: t=<ts>,sign=<hex>`) caducan a los 5 minutos.

Si KITCHAN está caído, el pedido queda guardado y el bot reintenta cada 30 s (máx. 20 intentos); `/api/status` muestra `orders_pending_kitchan`. KITCHAN es idempotente por `order_id`, así que un reintento nunca duplica el pedido.
