import logging
import uuid
import razorpay
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.payment import PaymentTransaction, TenantAiCredit
from app.models.credit_usage import CreditUsage
from app.schemas.payment import (
    CreateOrderRequest,
    CreateOrderResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)

logger = logging.getLogger(__name__)


def _get_razorpay_client() -> razorpay.Client:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise ValueError("Razorpay keys are not configured in environment.")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def get_or_create_balance(db: Session, tenant_id: uuid.UUID) -> float:
    credit = db.scalar(select(TenantAiCredit).where(TenantAiCredit.tenant_id == tenant_id))
    if not credit:
        credit = TenantAiCredit(tenant_id=tenant_id, balance=500.0)
        db.add(credit)
        db.commit()
        db.refresh(credit)
    return float(credit.balance)


def credits_for_tokens(total_tokens: int) -> float:
    """Credits charged for a number of tokens (prompt + completion)."""
    return round(max(0, total_tokens) / 1000.0 * settings.ai_credits_per_1k_tokens, 2)


def deduct_credits(
    db: Session,
    tenant_id: uuid.UUID,
    credits: float,
    *,
    conversation_id: uuid.UUID | None = None,
    description: str = "AI reply",
    model: str | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> float:
    """
    Deduct credits from a tenant's balance (clamped at zero) and record the
    usage. The balance row is locked FOR UPDATE. Returns the new balance.
    Callers gate AI usage up front with ``get_or_create_balance`` so no AI
    request is made when the balance is already zero; this records the actual
    cost of a reply that was produced.
    """
    credit = db.scalar(
        select(TenantAiCredit).where(TenantAiCredit.tenant_id == tenant_id).with_for_update()
    )
    if credit is None:
        credit = TenantAiCredit(tenant_id=tenant_id, balance=500.0)
        db.add(credit)
        db.flush()

    charge = round(max(0.0, float(credits)), 2)
    new_balance = round(max(0.0, float(credit.balance) - charge), 2)
    credit.balance = new_balance
    db.add(CreditUsage(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        description=description[:255],
        model=model,
        tokens_in=max(0, tokens_in),
        tokens_out=max(0, tokens_out),
        credits=charge,
        balance_after=new_balance,
    ))
    db.commit()
    return new_balance


def list_usage(db: Session, tenant_id: uuid.UUID, limit: int = 50) -> list[CreditUsage]:
    return list(db.scalars(
        select(CreditUsage)
        .where(CreditUsage.tenant_id == tenant_id)
        .order_by(CreditUsage.created_at.desc())
        .limit(limit)
    ).all())


def create_order(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None,
    data: CreateOrderRequest,
) -> CreateOrderResponse:
    client = _get_razorpay_client()
    amount_in_paise = int(round(data.amount * 100))
    receipt = f"rcpt_{uuid.uuid4().hex[:12]}"

    try:
        razorpay_order = client.order.create(
            {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": receipt,
                "notes": {
                    "tenant_id": str(tenant_id),
                    "credits": str(data.credits),
                },
            }
        )
    except Exception as exc:
        logger.exception("Failed to create Razorpay order: %s", exc)
        raise ValueError(f"Razorpay order creation failed: {exc}")

    transaction = PaymentTransaction(
        tenant_id=tenant_id,
        user_id=user_id,
        razorpay_order_id=razorpay_order["id"],
        amount=data.amount,
        currency="INR",
        credits_amount=data.credits,
        status="created",
        description=data.description or f"{int(data.credits)} AI Credits",
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return CreateOrderResponse(
        order_id=razorpay_order["id"],
        key_id=settings.razorpay_key_id,
        amount=data.amount,
        currency="INR",
        credits=data.credits,
    )


def verify_payment(
    db: Session,
    tenant_id: uuid.UUID,
    data: VerifyPaymentRequest,
) -> VerifyPaymentResponse:
    client = _get_razorpay_client()

    params_dict = {
        "razorpay_order_id": data.razorpay_order_id,
        "razorpay_payment_id": data.razorpay_payment_id,
        "razorpay_signature": data.razorpay_signature,
    }

    try:
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        logger.warning(
            "Razorpay signature verification failed for order %s", data.razorpay_order_id
        )
        raise ValueError("Invalid Razorpay payment signature.")

    transaction = db.scalar(
        select(PaymentTransaction).where(
            PaymentTransaction.tenant_id == tenant_id,
            PaymentTransaction.razorpay_order_id == data.razorpay_order_id,
        )
    )
    if not transaction:
        raise ValueError("Payment transaction not found.")

    if transaction.status == "paid":
        # Idempotent response if already marked paid
        balance = get_or_create_balance(db, tenant_id)
        return VerifyPaymentResponse(
            success=True,
            message="Payment already processed.",
            credits_added=float(transaction.credits_amount),
            new_balance=balance,
            transaction_id=transaction.id,
        )

    # Mark as paid
    transaction.status = "paid"
    transaction.razorpay_payment_id = data.razorpay_payment_id
    transaction.razorpay_signature = data.razorpay_signature

    credit = db.scalar(select(TenantAiCredit).where(TenantAiCredit.tenant_id == tenant_id))
    if not credit:
        credit = TenantAiCredit(tenant_id=tenant_id, balance=500.0)
        db.add(credit)

    credit.balance = float(credit.balance) + float(transaction.credits_amount)
    db.commit()
    db.refresh(transaction)
    db.refresh(credit)

    return VerifyPaymentResponse(
        success=True,
        message="Payment verified successfully. Credits have been added to your balance.",
        credits_added=float(transaction.credits_amount),
        new_balance=float(credit.balance),
        transaction_id=transaction.id,
    )


def list_transactions(
    db: Session,
    tenant_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[PaymentTransaction], int]:
    query = select(PaymentTransaction).where(PaymentTransaction.tenant_id == tenant_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(PaymentTransaction.created_at.desc()).offset(skip).limit(limit)
    ).all()
    return list(items), total
