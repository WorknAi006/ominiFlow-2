import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.ecommerce import Order, OrderItem, OrderStatus, Product
from app.schemas.ecommerce import (
    EcommerceOverview,
    OrderCreate,
    OrderUpdate,
    ProductCreate,
    ProductUpdate,
)

class EcommerceService:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self, tenant_id: uuid.UUID) -> EcommerceOverview:
        total_products = self.db.scalar(select(func.count(Product.id)).where(Product.tenant_id == tenant_id)) or 0
        total_orders = self.db.scalar(select(func.count(Order.id)).where(Order.tenant_id == tenant_id)) or 0
        pending_orders = self.db.scalar(
            select(func.count(Order.id)).where(
                Order.tenant_id == tenant_id,
                Order.status == OrderStatus.PENDING
            )
        ) or 0
        total_revenue = self.db.scalar(
            select(func.sum(Order.total_amount)).where(
                Order.tenant_id == tenant_id,
                Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PROCESSING])
            )
        ) or 0.0

        return EcommerceOverview(
            total_products=total_products,
            total_orders=total_orders,
            pending_orders=pending_orders,
            total_revenue=float(total_revenue)
        )

    # Products
    def create_product(self, tenant_id: uuid.UUID, data: ProductCreate) -> Product:
        product = Product(**data.model_dump(), tenant_id=tenant_id)
        self.db.add(product)
        try:
            self.db.commit()
            self.db.refresh(product)
            return product
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Product SKU already exists")

    def get_products(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100, search: Optional[str] = None
    ) -> Tuple[List[Product], int]:
        query = select(Product).where(Product.tenant_id == tenant_id)
        if search:
            query = query.where(Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%"))
        
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        products = self.db.scalars(query.order_by(Product.created_at.desc()).offset(skip).limit(limit)).all()
        return list(products), total

    def get_product(self, tenant_id: uuid.UUID, product_id: uuid.UUID) -> Optional[Product]:
        return self.db.scalar(select(Product).where(Product.tenant_id == tenant_id, Product.id == product_id))

    def update_product(self, tenant_id: uuid.UUID, product_id: uuid.UUID, data: ProductUpdate) -> Optional[Product]:
        product = self.get_product(tenant_id, product_id)
        if not product:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        try:
            self.db.commit()
            self.db.refresh(product)
            return product
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Product SKU already exists")

    def delete_product(self, tenant_id: uuid.UUID, product_id: uuid.UUID) -> bool:
        product = self.get_product(tenant_id, product_id)
        if not product:
            return False
        self.db.delete(product)
        self.db.commit()
        return True

    # Orders
    def create_order(self, tenant_id: uuid.UUID, data: OrderCreate) -> Order:
        if data.contact_id:
            from app.models.contact import Contact
            contact = self.db.scalar(select(Contact).where(Contact.tenant_id == tenant_id, Contact.id == data.contact_id))
            if not contact:
                raise ValueError("Contact not found or does not belong to this tenant")

        order_data = data.model_dump(exclude={"items"})
        order = Order(**order_data, tenant_id=tenant_id, total_amount=0.0)
        self.db.add(order)
        
        total_amount = 0.0
        for item_data in data.items:
            product = self.get_product(tenant_id, item_data.product_id)
            if not product:
                raise ValueError(f"Product {item_data.product_id} not found or does not belong to this tenant")
            
            unit_price = float(product.price)
            total_price = unit_price * item_data.quantity
            total_amount += total_price
            
            item = OrderItem(
                tenant_id=tenant_id,
                order=order,
                product_id=product.id,
                quantity=item_data.quantity,
                unit_price=unit_price,
                total_price=total_price,
            )
            self.db.add(item)
            
        order.total_amount = total_amount
            
        try:
            self.db.commit()
            self.db.refresh(order)
            return order
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Order number already exists")

    def get_orders(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100, search: Optional[str] = None
    ) -> Tuple[List[Order], int]:
        query = select(Order).where(Order.tenant_id == tenant_id)
        if search:
            query = query.where(Order.order_number.ilike(f"%{search}%"))
            
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        orders = self.db.scalars(query.order_by(Order.created_at.desc()).offset(skip).limit(limit)).all()
        return list(orders), total

    def get_order(self, tenant_id: uuid.UUID, order_id: uuid.UUID) -> Optional[Order]:
        return self.db.scalar(select(Order).where(Order.tenant_id == tenant_id, Order.id == order_id))

    def update_order_status(self, tenant_id: uuid.UUID, order_id: uuid.UUID, status: OrderStatus) -> Optional[Order]:
        order = self.get_order(tenant_id, order_id)
        if not order:
            return None

        # Define valid transitions
        valid_transitions = {
            OrderStatus.PENDING: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
            OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
            OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.REFUNDED},
            OrderStatus.DELIVERED: {OrderStatus.REFUNDED},
            OrderStatus.CANCELLED: set(),
            OrderStatus.REFUNDED: set(),
        }
        
        if order.status == status:
            return order
            
        if status not in valid_transitions.get(order.status, set()):
            raise ValueError(f"Invalid transition from {order.status} to {status}")

        order.status = status
        self.db.commit()
        self.db.refresh(order)
        return order
