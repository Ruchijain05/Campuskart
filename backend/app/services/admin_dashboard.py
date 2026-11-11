from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.auth import SellerApplication, User, UserRole
from app.models.order import Order
from app.models.product import Product
from app.models.review import Review
from app.schemas.admin_dashboard import (
    AdminActivity,
    AdminDailySummary,
    AdminDashboardRead,
)


def get_admin_dashboard(db: Session) -> AdminDashboardRead:
    total_users = db.scalar(select(func.count(User.id))) or 0
    all_users = list(db.scalars(select(User)).all())
    buyers = sum(UserRole.BUYER.value in (user.roles or []) for user in all_users)
    sellers = sum(UserRole.SELLER.value in (user.roles or []) for user in all_users)
    delivery_persons = sum(UserRole.DELIVERY_PERSON.value in (user.roles or []) for user in all_users)
    total_products = db.scalar(select(func.count(Product.id))) or 0
    total_orders = db.scalar(select(func.count(Order.id))) or 0
    total_revenue = db.scalar(
        select(func.coalesce(func.sum(Order.total), 0)).where(Order.status != "cancelled")
    ) or Decimal("0.00")

    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=6)
    cutoff = datetime.combine(first_day, time.min, tzinfo=timezone.utc)
    day_values = [first_day + timedelta(days=offset) for offset in range(7)]
    order_rows = db.execute(
        select(func.date(Order.created_at), func.count(Order.id))
        .where(Order.created_at >= cutoff)
        .group_by(func.date(Order.created_at))
    ).all()
    user_rows = db.execute(
        select(func.date(User.created_at), func.count(User.id))
        .where(User.created_at >= cutoff)
        .group_by(func.date(User.created_at))
    ).all()
    orders_by_day = {str(day): count for day, count in order_rows}
    users_by_day = {str(day): count for day, count in user_rows}
    daily_summary = [
        AdminDailySummary(
            date=day.isoformat(),
            orders=orders_by_day.get(day.isoformat(), 0),
            registrations=users_by_day.get(day.isoformat(), 0),
        )
        for day in day_values
    ]

    activities: list[AdminActivity] = []
    for user in db.scalars(select(User).order_by(User.created_at.desc()).limit(8)):
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        activities.append(AdminActivity(
            id=f"user-{user.id}", kind="user",
            title="New account registered",
            detail=f"{user.full_name} joined as a {role}.",
            created_at=user.created_at,
        ))
    for product in db.scalars(select(Product).order_by(Product.created_at.desc()).limit(8)):
        activities.append(AdminActivity(
            id=f"product-{product.id}", kind="product",
            title="Product listed", detail=product.name,
            created_at=product.created_at,
        ))
    for order in db.scalars(select(Order).order_by(Order.created_at.desc()).limit(8)):
        activities.append(AdminActivity(
            id=f"order-{order.id}", kind="order",
            title=f"Order #{order.id} placed",
            detail=f"Current status: {order.status} · {order.total}",
            created_at=order.created_at,
        ))
    for review, product_name in db.execute(
        select(Review, Product.name)
        .join(Product, Product.id == Review.product_id)
        .order_by(Review.created_at.desc())
        .limit(8)
    ):
        activities.append(AdminActivity(
            id=f"review-{review.id}", kind="review",
            title="Product review added",
            detail=f"{product_name} · {review.rating}/5 stars",
            created_at=review.created_at,
        ))
    for application, user_name in db.execute(
        select(SellerApplication, User.full_name)
        .join(User, User.id == SellerApplication.user_id)
        .order_by(SellerApplication.created_at.desc())
        .limit(8)
    ):
        activities.append(AdminActivity(
            id=f"seller-application-{application.id}", kind="application",
            title="Seller application submitted",
            detail=f"{user_name} · {application.status.value if hasattr(application.status, 'value') else application.status}",
            created_at=application.created_at,
        ))
    activities.sort(key=lambda item: item.created_at, reverse=True)

    return AdminDashboardRead(
        total_users=total_users,
        buyers=buyers,
        sellers=sellers,
        delivery_persons=delivery_persons,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        daily_summary=daily_summary,
        recent_activities=activities[:10],
    )
