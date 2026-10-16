import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CreateOrderRequest(BaseModel):
    credits: float = Field(..., gt=0, description="Number of AI credits to purchase")
    amount: float = Field(..., gt=0, description="Total amount in INR (including GST)")
    description: str | None = Field(None, description="Optional description of the purchase")


class CreateOrderResponse(BaseModel):
    order_id: str
    key_id: str
    amount: float
    currency: str
    credits: float


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    success: bool
    message: str
    credits_added: float
    new_balance: float
    transaction_id: uuid.UUID


class CreditBalanceResponse(BaseModel):
    balance: float


class PaymentTransactionResponse(BaseModel):
    id: uuid.UUID
    razorpay_order_id: str
    razorpay_payment_id: str | None
    amount: float
    currency: str
    credits_amount: float
    status: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    items: list[PaymentTransactionResponse]
    total: int


class CreditUsageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID | None
    description: str
    model: str | None
    tokens_in: int
    tokens_out: int
    credits: float
    balance_after: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UsageListResponse(BaseModel):
    items: list[CreditUsageResponse]
    total_credits: float
    total_count: int
