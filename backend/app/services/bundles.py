from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.bundle import ProductBundle, ProductBundleItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.bundles import BundleCreate, BundleOrderCreate, BundleRead, BundleUpdate
from app.services.email_notifications import send_email
from app.services.low_stock import update_low_stock_alert_state
from app.services.notifications import create_notification
from app.services.shipping import order_shipping_values
from app.services.pickup import apply_fulfillment, active_location

CENT = Decimal("0.01")


def _bundle_read(db: Session, bundle: ProductBundle) -> BundleRead:
    rows = db.execute(
        select(ProductBundleItem, Product)
        .join(Product, Product.id == ProductBundleItem.product_id)
        .where(ProductBundleItem.bundle_id == bundle.id)
        .order_by(ProductBundleItem.id)
    ).all()
    original = Decimal("0.00")
    max_bundles = 20
    available = bool(rows) and bundle.is_active
    items = []
    for component, product in rows:
        price = product.current_price
        original += price * component.quantity
        component_stock = product.stock if product.is_active else 0
        max_bundles = min(max_bundles, component_stock // component.quantity)
        available = available and product.is_active and component_stock >= component.quantity
        items.append({
            "product_id": product.id,
            "product_name": product.name,
            "image_url": product.image_url,
            "quantity": component.quantity,
            "unit_price": price,
            "available_stock": component_stock,
        })
    original = original.quantize(CENT)
    payable = min(bundle.special_price, original).quantize(CENT)
    discount = max(Decimal("0.00"), original - payable).quantize(CENT)
    percent = (discount * Decimal("100") / original).quantize(CENT, rounding=ROUND_HALF_UP) if original else Decimal("0.00")
    return BundleRead(
        id=bundle.id,
        name=bundle.name,
        description=bundle.description,
        special_price=bundle.special_price,
        payable_price=payable,
        original_price=original,
        discount_amount=discount,
        discount_percentage=percent,
        is_active=bundle.is_active,
        available=available and max_bundles > 0 and len(items) >= 2,
        max_bundles=max(0, max_bundles),
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
        items=items,
    )


def list_bundles(db: Session, *, include_inactive: bool = False) -> list[BundleRead]:
    statement = select(ProductBundle).order_by(ProductBundle.created_at.desc(), ProductBundle.id.desc())
    if not include_inactive:
        statement = statement.where(ProductBundle.is_active.is_(True))
    bundles = db.scalars(statement).all()
    results = [_bundle_read(db, bundle) for bundle in bundles]
    return results if include_inactive else [bundle for bundle in results if len(bundle.items) >= 2]


def get_bundle(db: Session, bundle_id: int, *, include_inactive: bool = False) -> BundleRead | None:
    bundle = db.get(ProductBundle, bundle_id)
    if bundle is None or (not include_inactive and not bundle.is_active):
        return None
    result = _bundle_read(db, bundle)
    if len(result.items) < 2 and not include_inactive:
        return None
    return result


def _validate_components(db: Session, details: BundleCreate | BundleUpdate) -> list[Product]:
    ids = [component.product_id for component in details.items]
    products = list(db.scalars(select(Product).where(Product.id.in_(ids)).order_by(Product.id)).all())
    by_id = {product.id: product for product in products}
    if len(by_id) != len(ids):
        raise HTTPException(status_code=422, detail="One or more selected products no longer exist.")
    if any(not by_id[product_id].is_active for product_id in ids):
        raise HTTPException(status_code=422, detail="Bundles can only contain active products.")
    regular_total = sum((by_id[item.product_id].current_price * item.quantity for item in details.items), Decimal("0.00"))
    if details.special_price >= regular_total:
        raise HTTPException(status_code=422, detail="The bundle price must be lower than the combined product price.")
    return [by_id[product_id] for product_id in ids]


def create_bundle(db: Session, details: BundleCreate) -> BundleRead:
    _validate_components(db, details)
    bundle = ProductBundle(
        name=details.name.strip(),
        description=details.description.strip() if details.description else None,
        special_price=details.special_price,
        is_active=details.is_active,
        items=[ProductBundleItem(product_id=item.product_id, quantity=item.quantity) for item in details.items],
    )
    db.add(bundle)
    db.commit()
    db.refresh(bundle)
    return _bundle_read(db, bundle)


def update_bundle(db: Session, bundle_id: int, details: BundleUpdate) -> BundleRead:
    bundle = db.scalar(select(ProductBundle).where(ProductBundle.id == bundle_id).with_for_update())
    if bundle is None:
        raise HTTPException(status_code=404, detail="Bundle not found.")
    _validate_components(db, details)
    bundle.name = details.name.strip()
    bundle.description = details.description.strip() if details.description else None
    bundle.special_price = details.special_price
    bundle.is_active = details.is_active
    bundle.items.clear()
    bundle.items.extend(ProductBundleItem(product_id=item.product_id, quantity=item.quantity) for item in details.items)
    db.commit()
    db.refresh(bundle)
    return _bundle_read(db, bundle)


def disable_bundle(db: Session, bundle_id: int) -> BundleRead:
    bundle = db.get(ProductBundle, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Bundle not found.")
    bundle.is_active = False
    db.commit()
    db.refresh(bundle)
    return _bundle_read(db, bundle)


def place_bundle_order(db: Session, buyer_id: int, bundle_id: int, details: BundleOrderCreate) -> Order:
    bundle = db.scalar(select(ProductBundle).where(ProductBundle.id == bundle_id).with_for_update())
    if bundle is None or not bundle.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle is unavailable.")
    components = db.execute(
        select(ProductBundleItem, Product)
        .join(Product, Product.id == ProductBundleItem.product_id)
        .where(ProductBundleItem.bundle_id == bundle_id)
        .order_by(Product.id)
        .with_for_update()
    ).all()
    if len(components) < 2:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This bundle is incomplete and cannot be purchased.")
    for component, product in components:
        required = component.quantity * details.quantity
        if not product.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{product.name} in this bundle is unavailable.")
        if product.stock < required:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Only {product.stock // component.quantity} bundle(s) remain available.")

    original_subtotal = sum(
        (product.current_price * component.quantity * details.quantity for component, product in components),
        Decimal("0.00"),
    ).quantize(CENT)
    bundle_subtotal = min(bundle.special_price * details.quantity, original_subtotal).quantize(CENT)
    discount = max(Decimal("0.00"), original_subtotal - bundle_subtotal).quantize(CENT)
    if details.delivery_method == "campus_pickup":
        active_location(db, details.pickup_location_id)
        shipping_fee, estimated_delivery_at = Decimal("0.00"), None
    else:
        shipping_fee, estimated_delivery_at = order_shipping_values(db)
    order_total = (bundle_subtotal + shipping_fee).quantize(CENT)
    order = Order(
        user_id=buyer_id,
        status="placed",
        payment_method="cod",
        payment_status="pending",
        discount_description=f"Bundle offer: {bundle.name}"[:80],
        delivery_name=details.delivery_name,
        delivery_phone=details.delivery_phone,
        address_line=details.address_line,
        city=details.city,
        state=details.state,
        postal_code=details.postal_code,
        subtotal=original_subtotal,
        discount_amount=discount,
        shipping_fee=shipping_fee,
        estimated_delivery_at=estimated_delivery_at,
        total=order_total,
    )
    apply_fulfillment(db, order, details)
    for component, product in components:
        quantity = component.quantity * details.quantity
        line_total = (product.current_price * quantity).quantize(CENT)
        order.items.append(OrderItem(
            product_id=product.id,
            seller_id=product.seller_id,
            product_name=f"{bundle.name} - {product.name}"[:150],
            unit_price=product.current_price,
            quantity=quantity,
            line_total=line_total,
        ))
        product.stock -= quantity
        update_low_stock_alert_state(db, product)
    db.add(order)
    db.flush()
    buyer = db.get(User, buyer_id)
    create_notification(
        db,
        user_id=buyer_id,
        kind="order_status",
        title="Bundle order placed",
        message=f"Your bundle order #{order.id} has been placed successfully.",
        link=f"/orders/{order.id}",
    )
    order_id = order.id
    email = buyer.email if buyer else None
    buyer_name = buyer.full_name if buyer else "Buyer"
    lines = [f"- {item.product_name} x {item.quantity}" for item in order.items]
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    if email:
        send_email(
            email,
            f"CampusKart bundle order confirmation #{order_id}",
            f"Hi {buyer_name},\n\nYour bundle order #{order_id} has been placed.\n\nItems:\n{chr(10).join(lines)}\n\nBundle discount: INR {discount}\nDelivery: INR {shipping_fee}\nTotal due on delivery: INR {order_total}.",
        )
    return order
