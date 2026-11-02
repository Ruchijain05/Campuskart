from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.product import Product
from app.models.question import ProductQuestion
from app.schemas.questions import ProductAnswerCreate, ProductQuestionCreate, ProductQuestionRead
from app.services.notifications import create_notification


def _read(question: ProductQuestion, product_name: str, buyer_name: str) -> ProductQuestionRead:
    return ProductQuestionRead(
        id=question.id,
        product_id=question.product_id,
        product_name=product_name,
        buyer_name=buyer_name.split()[0] if buyer_name.strip() else "Buyer",
        question=question.question,
        answer=question.answer,
        created_at=question.created_at,
        answered_at=question.answered_at,
    )


def list_product_questions(db: Session, product_id: int) -> list[ProductQuestionRead]:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    rows = db.execute(
        select(ProductQuestion, User.full_name)
        .join(User, User.id == ProductQuestion.buyer_id)
        .where(ProductQuestion.product_id == product_id)
        .order_by(ProductQuestion.created_at.desc(), ProductQuestion.id.desc())
    ).all()
    return [_read(question, product.name, buyer_name) for question, buyer_name in rows]


def list_buyer_questions(db: Session, buyer_id: int) -> list[ProductQuestionRead]:
    rows = db.execute(
        select(ProductQuestion, Product.name, User.full_name)
        .join(Product, Product.id == ProductQuestion.product_id)
        .join(User, User.id == ProductQuestion.buyer_id)
        .where(ProductQuestion.buyer_id == buyer_id)
        .order_by(ProductQuestion.created_at.desc(), ProductQuestion.id.desc())
    ).all()
    return [_read(question, product_name, buyer_name) for question, product_name, buyer_name in rows]


def ask_question(db: Session, *, product_id: int, buyer: User, data: ProductQuestionCreate) -> ProductQuestionRead:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    question = ProductQuestion(product_id=product.id, buyer_id=buyer.id, question=data.question)
    db.add(question)
    db.commit()
    db.refresh(question)
    return _read(question, product.name, buyer.full_name)


def answer_question(
    db: Session,
    *,
    question_id: int,
    seller_id: int,
    data: ProductAnswerCreate,
) -> ProductQuestionRead:
    row = db.execute(
        select(ProductQuestion, Product, User)
        .join(Product, Product.id == ProductQuestion.product_id)
        .join(User, User.id == ProductQuestion.buyer_id)
        .where(ProductQuestion.id == question_id, Product.seller_id == seller_id)
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    question, product, buyer = row
    was_answered = question.answer is not None
    question.answer = data.answer
    question.answered_at = datetime.now(timezone.utc)
    if not was_answered:
        create_notification(
            db,
            user_id=buyer.id,
            kind="product_question_answered",
            title="Your product question was answered",
            message=f"The seller answered your question about {product.name}.",
            link=f"/products/{product.id}",
        )
    db.commit()
    db.refresh(question)
    return _read(question, product.name, buyer.full_name)
