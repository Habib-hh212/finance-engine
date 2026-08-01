import uuid
from typing import Optional

from pydantic import BaseModel


class ProductOut(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    unit_variable_cost: Optional[float]

    model_config = {"from_attributes": True}


class ProductUpdate(BaseModel):
    unit_variable_cost: float
