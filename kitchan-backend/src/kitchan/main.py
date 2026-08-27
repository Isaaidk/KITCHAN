from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.kitchan.modules.integraciones.uber.infrastructure.controllers.webhook_api import (
    router as uber_webhook_router
)

from src.kitchan.modules.integraciones.uber.infrastructure.controllers.oauth_api import (
    router as uber_oauth_router
)

from src.kitchan.modules.integraciones.uber.infrastructure.controllers import (
    orders_api
)

from src.kitchan.modules.restaurantes.infrastructure.rest_api import (
    router as onboarding_router
)

from src.kitchan.modules.usuarios.infrastructure.rest_api import (
    router as usuarios_router
)


app = FastAPI(
    title="KITCHAN API",
    description="Sistema centralizado de pedidos para Vangalia",
    version="1.0.0",
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

app.include_router(
    usuarios_router
)

app.include_router(
    onboarding_router
)

app.include_router(
    uber_webhook_router
)

app.include_router(
    uber_oauth_router
)

app.include_router(
    orders_api.router
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "mensaje":
            "¡El núcleo de KITCHAN está en línea y operativo!"
    }