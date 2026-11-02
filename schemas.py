from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import List

class UserCreate(BaseModel):
    name: str
    email: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str

class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float
    stock: int

class OrderCreate(BaseModel):
    user_id: int
    product_ids: List[int] = Field(
        description="Ids de los productos del pedido; repetir un id pide una unidad más de ese producto",
    )

class OrderCreated(BaseModel):
    status: str
    order_id: int
    total: float

class OrderItemOut(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float = Field(description="Precio por unidad ya con descuento, tal como se cobró")

class OrderOut(BaseModel):
    id: int
    created_at: datetime
    total_price: float
    items: List[OrderItemOut]
