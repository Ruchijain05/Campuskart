from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.delivery import DeliveryJobAssign, DeliveryJobRead, DeliveryJobStatusUpdate, DeliveryPersonCreate, DeliveryPersonRead
from app.schemas.orders import OrderRead
from app.services import delivery as delivery_service

router = APIRouter(prefix="/delivery", tags=["campus delivery"])


@router.get("/people", response_model=list[DeliveryPersonRead])
def list_people(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    return delivery_service.list_delivery_people(db)


@router.post("/people", response_model=DeliveryPersonRead, status_code=201)
def create_person(details: DeliveryPersonCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    return delivery_service.create_delivery_person(db, details)


@router.get("/eligible-orders", response_model=list[OrderRead])
def list_eligible_orders(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    return delivery_service.list_eligible_orders(db)


@router.get("/jobs/admin", response_model=list[DeliveryJobRead])
def list_all_jobs(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    return delivery_service.list_jobs(db)


@router.post("/jobs/{order_id}/assign", response_model=DeliveryJobRead)
def assign_job(order_id: int, details: DeliveryJobAssign, db: Session = Depends(get_db), admin: User = Depends(require_roles(UserRole.ADMIN))):
    return delivery_service.assign_job(db, order_id=order_id, delivery_person_id=details.delivery_person_id, admin_id=admin.id)


@router.get("/jobs", response_model=list[DeliveryJobRead])
def list_my_jobs(db: Session = Depends(get_db), staff: User = Depends(require_roles(UserRole.DELIVERY_PERSON))):
    return delivery_service.list_jobs(db, delivery_person_id=staff.id)


@router.patch("/jobs/{job_id}", response_model=DeliveryJobRead)
def update_job(job_id: int, update_in: DeliveryJobStatusUpdate, db: Session = Depends(get_db), staff: User = Depends(require_roles(UserRole.DELIVERY_PERSON))):
    return delivery_service.update_job_status(
        db, job_id=job_id, delivery_person_id=staff.id,
        next_status=update_in.status, failure_note=update_in.failure_note,
    )
