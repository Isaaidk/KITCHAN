from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.kitchan.modules.restaurantes.infrastructure.rest_api import \
    router as onboarding_router
from src.kitchan.modules.usuarios.infrastructure.rest_api import \
    router as usuarios_router

app = FastAPI(
    title="KITCHAN API",
    description="Sistema centralizado de pedidos para Vangalia",
    version="1.0.0",
)

# Configuración CORS para que React (Paulo) pueda conectarse sin bloqueos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción se cambia por la URL de React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(usuarios_router)
app.include_router(onboarding_router)


@app.get("/")
async def root():
    return {"mensaje": "¡El núcleo de KITCHAN está en línea y operativo!"}
