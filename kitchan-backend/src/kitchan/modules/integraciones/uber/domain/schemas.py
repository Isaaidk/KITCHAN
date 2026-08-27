from pydantic import BaseModel, Field

class UberProvisionRequest(BaseModel):
    restaurante_id: str = Field(..., description="ID interno en KITCHAN (Ej: TEST-001)")
    store_id: str = Field(..., description="UUID de la tienda en Uber Eats")