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

from src.kitchan.modules.restaurantes.infrastructure.rest_api import (
    router as onboarding_router,
)

from src.kitchan.modules.usuarios.infrastructure.rest_api import (
    router as usuarios_router,
)

from src.kitchan.modules.pedidos.infrastructure.rest_api import router as pedidos_router

from src.kitchan.modules.pedidos.infrastructure.controllers.websocket_api import (
    router as pedidos_ws_router,
)

from src.kitchan.modules.pedidos.infrastructure.websocket.redis_subscriber import (
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

app.include_router(pedidos_router)

app.include_router(pedidos_ws_router)

app.include_router(reportes_router)


# ============================================================
# ROOT
# ============================================================


@app.get("/")
async def root():

    return {"mensaje": "¡El núcleo de KITCHAN está en línea y operativo!"}
