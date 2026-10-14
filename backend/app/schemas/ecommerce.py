import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.ecommerce import OrderStatus

class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    is_available: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    is_available: Optional[bool] = None

class ProductRead(ProductBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProductListResponse(BaseModel):
    items: List[ProductRead]
    total: int


class OrderItemBase(BaseModel):
    product_id: Optional[uuid.UUID] = None
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    total_price: float = Field(..., ge=0)

class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0)

class OrderItemRead(OrderItemBase):
    id: uuid.UUID
    order_id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    contact_id: Optional[uuid.UUID] = None
    order_number: str = Field(..., max_length=100)
    status: OrderStatus = OrderStatus.PENDING
    currency: str = Field("USD", min_length=3, max_length=3)
    total_amount: float = Field(..., ge=0)

class OrderCreate(BaseModel):
    contact_id: Optional[uuid.UUID] = None
    order_number: str = Field(..., max_length=100)
    currency: str = Field("USD", min_length=3, max_length=3)
    items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None

class OrderRead(OrderBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemRead] = []
    
    model_config = ConfigDict(from_attributes=True)

class OrderListResponse(BaseModel):
    items: List[OrderRead]
    total: int


class EcommerceOverview(BaseModel):
    total_products: int
    total_orders: int
    pending_orders: int
    total_revenue: float
