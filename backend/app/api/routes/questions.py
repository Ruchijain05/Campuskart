from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.questions import ProductAnswerCreate, ProductQuestionCreate, ProductQuestionRead
from app.services import questions as question_service

router = APIRouter(tags=["product questions"])


@router.get("/products/{product_id}/questions", response_model=list[ProductQuestionRead])
def list_product_questions(product_id: int, db: Session = Depends(get_db)) -> list[ProductQuestionRead]:
    return question_service.list_product_questions(db, product_id)


@router.post(
    "/products/{product_id}/questions",
    response_model=ProductQuestionRead,
    status_code=status.HTTP_201_CREATED,
)
def ask_product_question(
    product_id: int,
    question_in: ProductQuestionCreate,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> ProductQuestionRead:
    return question_service.ask_question(db, product_id=product_id, buyer=buyer, data=question_in)


@router.get("/questions/mine", response_model=list[ProductQuestionRead])
def list_my_questions(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> list[ProductQuestionRead]:
    return question_service.list_buyer_questions(db, buyer.id)


@router.patch("/questions/{question_id}/answer", response_model=ProductQuestionRead)
def answer_product_question(
    question_id: int,
    answer_in: ProductAnswerCreate,
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.SELLER)),
) -> ProductQuestionRead:
    return question_service.answer_question(
        db,
        question_id=question_id,
        seller_id=seller.id,
        data=answer_in,
    )
