import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentTenant, DbSession
from app.models.ecommerce import OrderStatus
from app.schemas.ecommerce import (
    EcommerceOverview,
    OrderCreate,
    OrderRead,
    OrderUpdate,
    ProductCreate,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
    OrderListResponse,
)
from app.services.ecommerce import EcommerceService

router = APIRouter(prefix="/ecommerce", tags=["ecommerce"])


@router.get("/overview", response_model=EcommerceOverview)
def get_overview(
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = EcommerceService(db)
    return service.get_overview(tenant.id)


@router.post("/products", response_model=ProductRead)
def create_product(
    data: ProductCreate,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = EcommerceService(db)
    try:
        return service.create_product(tenant.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/products", response_model=ProductListResponse)
def get_products(
    tenant: CurrentTenant,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: str | None = None,
) -> Any:
    service = EcommerceService(db)
    products, total = service.get_products(tenant.id, skip, limit, search)
    return {"items": products, "total": total}


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(
    product_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = EcommerceService(db)
    product = service.get_product(tenant.id, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/products/{product_id}", response_model=ProductRead)
def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = EcommerceService(db)
    try:
        product = service.update_product(tenant.id, product_id, data)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/products/{product_id}")
def delete_product(
    product_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = EcommerceService(db)
    success = service.delete_product(tenant.id, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True}


@router.post("/orders", response_model=OrderRead)
def create_order(
    data: OrderCreate,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = EcommerceService(db)
    try:
        return service.create_order(tenant.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders", response_model=OrderListResponse)
def get_orders(
    tenant: CurrentTenant,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: str | None = None,
) -> Any:
    service = EcommerceService(db)
    orders, total = service.get_orders(tenant.id, skip, limit, search)
    return {"items": orders, "total": total}


@router.get("/orders/{order_id}", response_model=OrderRead)
def get_order(
    order_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = EcommerceService(db)
    order = service.get_order(tenant.id, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/orders/{order_id}", response_model=OrderRead)
def update_order(
    order_id: uuid.UUID,
    data: OrderUpdate,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = EcommerceService(db)
    if data.status:
        try:
            order = service.update_order_status(tenant.id, order_id, data.status)
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            return order
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    order = service.get_order(tenant.id, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
