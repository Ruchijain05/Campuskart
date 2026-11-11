from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.auth import User, UserRole
from app.models.delivery_job import DeliveryJob
from app.models.order import Order, OrderItem
from app.schemas.delivery import DeliveryPersonCreate
from app.schemas.delivery import DeliveryJobRead, DeliveryPersonRead, DeliverySellerContact
from app.services.email_notifications import send_email
from app.services.notifications import create_notification

NEXT_STATUS = {
    "assigned": {"collected_from_seller"},
    "collected_from_seller": {"ready_at_pickup", "delivery_issue"},
    "ready_at_pickup": {"collected_by_buyer", "delivery_issue"},
    "delivery_issue": set(),
    "collected_by_buyer": set(),
}


def create_delivery_person(db: Session, details: DeliveryPersonCreate) -> DeliveryPersonRead:
    email = str(details.email).casefold()
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    if user is None:
        raise HTTPException(status_code=404, detail="No CampusKart account uses that email. The person must register as a buyer first.")
    assigned = list(user.roles or [user.role.value])
    if UserRole.DELIVERY_PERSON.value in assigned:
        raise HTTPException(status_code=409, detail="This account already has delivery person access.")
    user.roles = [*assigned, UserRole.DELIVERY_PERSON.value]
    db.commit()
    db.refresh(user)
    return DeliveryPersonRead.model_validate(user)


def _job_read(db: Session, job: DeliveryJob, order: Order) -> DeliveryJobRead:
    buyer = db.get(User, order.user_id)
    rows = db.execute(
        select(OrderItem, User)
        .outerjoin(User, User.id == OrderItem.seller_id)
        .where(OrderItem.order_id == order.id)
        .order_by(OrderItem.id)
    ).all()
    sellers: dict[int, DeliverySellerContact] = {}
    products: list[str] = []
    for item, seller in rows:
        products.append(f"{item.product_name} × {item.quantity}")
        if seller is not None:
            contact = sellers.setdefault(seller.id, DeliverySellerContact(
                full_name=seller.full_name, phone_number=seller.phone_number, products=[]
            ))
            contact.products.append(f"{item.product_name} × {item.quantity}")
    return DeliveryJobRead(
        id=job.id, order_id=order.id, delivery_person_id=job.delivery_person_id,
        status=job.status, pickup_location_name=job.pickup_location_name,
        buyer_name=order.delivery_name, buyer_phone=order.delivery_phone,
        pickup_address=f"{order.address_line}, {order.city}, {order.state} {order.postal_code}",
        sellers=list(sellers.values()), products=products, failure_note=job.failure_note,
        assigned_at=job.assigned_at, collected_from_seller_at=job.collected_from_seller_at,
        ready_at_pickup_at=job.ready_at_pickup_at,
        collected_by_buyer_at=job.collected_by_buyer_at, updated_at=job.updated_at,
    )


def list_delivery_people(db: Session) -> list[User]:
    people = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.full_name, User.id)).all()
    return [person for person in people if UserRole.DELIVERY_PERSON.value in (person.roles or [])]


def list_eligible_orders(db: Session) -> list[Order]:
    orders = db.scalars(
        select(Order).options(joinedload(Order.items))
        .where(Order.delivery_method == "campus_pickup", Order.status.notin_({"cancelled", "delivered"}))
        .order_by(Order.created_at.asc())
    ).unique().all()
    assigned_ids = set(db.scalars(select(DeliveryJob.order_id)).all())
    return [order for order in orders if order.id not in assigned_ids
            and not (order.payment_method == "razorpay" and order.payment_status == "pending")
            and order.pickup_status == "awaiting_pickup"
            and order.items
            and all(item.fulfillment_status in {"packed", "shipped", "delivered"} for item in order.items)]


def list_jobs(db: Session, *, delivery_person_id: int | None = None) -> list[DeliveryJobRead]:
    query = select(DeliveryJob, Order).join(Order, Order.id == DeliveryJob.order_id)
    if delivery_person_id is not None:
        query = query.where(DeliveryJob.delivery_person_id == delivery_person_id)
    query = query.order_by(DeliveryJob.updated_at.desc(), DeliveryJob.id.desc())
    return [_job_read(db, job, order) for job, order in db.execute(query).all()]


def assign_job(db: Session, *, order_id: int, delivery_person_id: int, admin_id: int) -> DeliveryJobRead:
    order = db.scalar(select(Order).options(joinedload(Order.items)).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.delivery_method != "campus_pickup" or order.status in {"cancelled", "delivered"}:
        raise HTTPException(status_code=409, detail="Only active campus pickup orders can be assigned.")
    if order.payment_method == "razorpay" and order.payment_status == "pending":
        raise HTTPException(status_code=409, detail="An order must have verified payment before delivery assignment.")
    if not order.items or any(item.fulfillment_status not in {"packed", "shipped", "delivered"} for item in order.items):
        raise HTTPException(status_code=409, detail="Every seller must pack their items before assignment.")
    staff = db.scalar(select(User).where(User.id == delivery_person_id, User.is_active.is_(True)))
    if staff is not None and UserRole.DELIVERY_PERSON.value not in (staff.roles or []):
        staff = None
    if staff is None:
        raise HTTPException(status_code=404, detail="Approved delivery staff member not found.")
    job = db.scalar(select(DeliveryJob).where(DeliveryJob.order_id == order_id).with_for_update())
    if order.pickup_status != "awaiting_pickup" and not (job is not None and job.status == "delivery_issue"):
        raise HTTPException(status_code=409, detail="Only orders awaiting seller collection can be assigned.")
    if job is None:
        job = DeliveryJob(order_id=order.id, delivery_person_id=staff.id, assigned_by_id=admin_id,
                          pickup_location_name=order.pickup_location_name or "Campus pickup")
        db.add(job)
    else:
        if job.status not in {"assigned", "delivery_issue"}:
            raise HTTPException(status_code=409, detail="A job already in progress cannot be reassigned.")
        job.delivery_person_id = staff.id
        job.assigned_by_id = admin_id
        job.status = "assigned"
        job.failure_note = None
        job.assigned_at = datetime.now(timezone.utc)
        job.collected_from_seller_at = None
        job.ready_at_pickup_at = None
        job.collected_by_buyer_at = None
    order.pickup_status = "awaiting_pickup"
    seller_ids = {item.seller_id for item in order.items if item.seller_id is not None}
    db.commit()
    db.refresh(job)
    if staff.email:
        send_email(staff.email, f"CampusKart delivery job assigned: order #{order.id}",
                   f"Hi {staff.full_name},\n\nCollect order #{order.id} directly from the seller and take it to {job.pickup_location_name}. Sign in to CampusKart to view seller and buyer contact details.")
    for seller_id in seller_ids:
        seller = db.get(User, seller_id)
        if seller and seller.email:
            send_email(seller.email, f"CampusKart staff will collect order #{order.id}",
                       f"Hi {seller.full_name},\n\nCampusKart delivery staff have been assigned to collect your packed items for order #{order.id}. Please have them ready for handoff.")
    return _job_read(db, job, order)


def update_job_status(db: Session, *, job_id: int, delivery_person_id: int, next_status: str, failure_note: str | None) -> DeliveryJobRead:
    row = db.execute(
        select(DeliveryJob, Order).join(Order, Order.id == DeliveryJob.order_id)
        .where(DeliveryJob.id == job_id, DeliveryJob.delivery_person_id == delivery_person_id)
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Assigned delivery job not found.")
    job, order = row
    if next_status not in NEXT_STATUS.get(job.status, set()):
        raise HTTPException(status_code=409, detail=f"Job cannot move from {job.status} to {next_status}.")
    now = datetime.now(timezone.utc)
    job.status = next_status
    if next_status == "collected_from_seller":
        job.collected_from_seller_at = now
        seller_ids = {item.seller_id for item in order.items if item.seller_id is not None}
    elif next_status == "ready_at_pickup":
        job.ready_at_pickup_at = now
        job.failure_note = None
        order.pickup_status = "ready"
        create_notification(db, user_id=order.user_id, kind="order_status", title="Your campus pickup is ready",
                            message=f"Order #{order.id} is ready at {job.pickup_location_name}.",
                            link=f"/orders/{order.id}")
    elif next_status == "collected_by_buyer":
        job.collected_by_buyer_at = now
        order.pickup_status = "collected"
        order.status = "delivered"
        create_notification(db, user_id=order.user_id, kind="order_status", title="Order collected",
                            message=f"Order #{order.id} has been collected at {job.pickup_location_name}.",
                            link=f"/orders/{order.id}")
    elif next_status == "delivery_issue":
        if not failure_note or not failure_note.strip():
            raise HTTPException(status_code=422, detail="Add a short note describing the delivery issue.")
        job.failure_note = failure_note.strip()
        create_notification(db, user_id=order.user_id, kind="order_status", title="Pickup handoff delayed",
                            message=f"There is a delay with order #{order.id}. CampusKart staff will follow up.",
                            link=f"/orders/{order.id}")
    db.commit()
    db.refresh(job)
    if next_status == "collected_from_seller":
        for seller_id in seller_ids:
            seller = db.get(User, seller_id)
            if seller and seller.email:
                send_email(seller.email, f"CampusKart collected order #{order.id}",
                           f"Hi {seller.full_name},\n\nCampusKart staff have collected the packed items for order #{order.id} to take to {job.pickup_location_name}.")
    if next_status == "ready_at_pickup":
        buyer = db.get(User, order.user_id)
        if buyer and buyer.email:
            send_email(buyer.email, f"CampusKart order #{order.id} is ready for pickup",
                       f"Hi {buyer.full_name},\n\nYour order #{order.id} is ready for collection at {job.pickup_location_name}.\n\nPlease visit the selected campus pickup point and show your order details.")
    return _job_read(db, job, order)
