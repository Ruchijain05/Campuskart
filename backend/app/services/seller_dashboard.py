from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.schemas.seller_dashboard import SellerDashboardOrder, SellerDashboardRead


def get_seller_dashboard(db: Session, seller_id: int) -> SellerDashboardRead:
    total_products = db.scalar(
        select(func.count(Product.id)).where(Product.seller_id == seller_id)
    ) or 0

    sales_rows = db.execute(
        select(
            Order.id,
            Order.status,
            Order.created_at,
            OrderItem.quantity,
            OrderItem.line_total,
            OrderItem.product_name,
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(OrderItem.seller_id == seller_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).all()

    by_order: dict[int, dict] = {}
    total_sales = 0
    total_revenue = Decimal("0.00")
    for order_id, status, created_at, quantity, line_total, product_name in sales_rows:
        if status != "cancelled":
            total_sales += quantity
            total_revenue += line_total
        entry = by_order.setdefault(order_id, {
            "id": order_id,
            "status": status,
            "created_at": created_at,
            "item_count": 0,
            "subtotal": Decimal("0.00"),
            "products": [],
        })
        entry["item_count"] += quantity
        entry["subtotal"] += line_total
        entry["products"].append(f"{product_name} × {quantity}")

    recent_orders = [
        SellerDashboardOrder(**order)
        for order in list(by_order.values())[:5]
    ]
    active_order_count = sum(order["status"] != "cancelled" for order in by_order.values())
    return SellerDashboardRead(
        total_products=total_products,
        total_orders=active_order_count,
        total_sales=total_sales,
        total_revenue=total_revenue,
        recent_orders=recent_orders,
    )
