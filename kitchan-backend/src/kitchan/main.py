import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from src.kitchan.core.websockets_manager import connection_manager
from src.kitchan.modules.integraciones.uber.infrastructure.controllers.webhook_api import (
    router as uber_webhook_router,
)

from src.kitchan.modules.integraciones.uber.infrastructure.controllers.oauth_api import (
    router as uber_oauth_router,
)

from src.kitchan.modules.integraciones.uber.infrastructure.controllers import orders_api

# Composition root: registra las rutas de infraestructura de la integración
# PedidosYa (dispatch de pedidos + acciones del KDS), igual que ya hace con Uber.
from src.kitchan.modules.integraciones.pedidosya.infrastructure.controllers import (
    order_dispatch_api as pedidosya_dispatch_api,
    orders_api as pedidosya_orders_api,
)

# Composition root: registra las rutas de infraestructura de la integración
# Rappi (webhooks NEW_ORDER/ORDER_EVENT_CANCEL + acciones del KDS).
from src.kitchan.modules.integraciones.rappi.infrastructure.controllers import (
    webhook_api as rappi_webhook_api,
    orders_api as rappi_orders_api,
)

from src.kitchan.modules.restaurantes.infrastructure.rest_api import (
    router as onboarding_router,
)

from src.kitchan.modules.usuarios.infrastructure.rest_api import (
    router as usuarios_router,
)

from src.kitchan.modules.pedidos.infrastructure.rest_api import router as pedidos_router

from src.kitchan.modules.notificaciones.infrastructure.websocket_api import (
    router as pedidos_ws_router,
)

from src.kitchan.modules.notificaciones.infrastructure.redis_subscriber import (
    iniciar_subscriber,
)

from src.kitchan.modules.pedidos.infrastructure.tareas.auto_cancelar import (
    iniciar_auto_cancelador,
)

from src.kitchan.modules.reportes.infrastructure.rest_api import (
    router as reportes_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.getenv("REDIS_URL")
    subscriber_task = iniciar_subscriber(redis_url, connection_manager)
    auto_cancelador_task = iniciar_auto_cancelador(redis_url)
    yield
    subscriber_task.cancel()
    auto_cancelador_task.cancel()


app = FastAPI(
    title="KITCHAN API",
    description="Sistema centralizado de pedidos para Vangalia",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(usuarios_router)

app.include_router(onboarding_router)

app.include_router(uber_webhook_router)

app.include_router(uber_oauth_router)

app.include_router(orders_api.router)

app.include_router(pedidosya_dispatch_api.router)

app.include_router(pedidosya_orders_api.router)

app.include_router(rappi_webhook_api.router)

app.include_router(rappi_orders_api.router)

app.include_router(pedidos_router)

app.include_router(pedidos_ws_router)

app.include_router(reportes_router)


# ============================================================
# ROOT
# ============================================================


@app.get("/")
async def root():

    return {"mensaje": "¡El núcleo de KITCHAN está en línea y operativo!"}
