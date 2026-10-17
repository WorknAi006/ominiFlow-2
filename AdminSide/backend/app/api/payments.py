from typing import Any
from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentTenant, CurrentUser, DbSession
from app.schemas.payment import (
    CreditBalanceResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    TransactionListResponse,
    UsageListResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/balance", response_model=CreditBalanceResponse)
def get_balance(
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    balance = payment_service.get_or_create_balance(db, tenant.id)
    return CreditBalanceResponse(balance=balance)


@router.post("/create-order", response_model=CreateOrderResponse)
def create_order(
    data: CreateOrderRequest,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: DbSession,
) -> Any:
    try:
        return payment_service.create_order(db, tenant.id, user.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/verify", response_model=VerifyPaymentResponse)
def verify_payment(
    data: VerifyPaymentRequest,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    try:
        return payment_service.verify_payment(db, tenant.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/transactions", response_model=TransactionListResponse)
def get_transactions(
    tenant: CurrentTenant,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    items, total = payment_service.list_transactions(db, tenant.id, skip=skip, limit=limit)
    return TransactionListResponse(items=items, total=total)


@router.get("/usage", response_model=UsageListResponse)
def get_usage(
    tenant: CurrentTenant,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
) -> Any:
    items = payment_service.list_usage(db, tenant.id, limit=limit)
    total_credits = round(sum(float(u.credits) for u in items), 2)
    return UsageListResponse(items=items, total_credits=total_credits, total_count=len(items))
