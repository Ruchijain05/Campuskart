from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.models.conversation import Conversation, ConversationMessage
from app.models.notification import Notification
from app.models.product import Product
from app.schemas.conversations import ConversationDetail, ConversationRead, MessageCreate, MessageRead, StartConversation
from app.services.notifications import create_notification


def _ensure_participant(conversation: Conversation, user: User) -> None:
    if user.id not in (conversation.buyer_id, conversation.seller_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")


def _summary(db: Session, conversation: Conversation, user: User) -> ConversationRead:
    product = db.get(Product, conversation.product_id)
    buyer = db.get(User, conversation.buyer_id)
    seller = db.get(User, conversation.seller_id)
    last = db.scalar(select(ConversationMessage.body).where(
        ConversationMessage.conversation_id == conversation.id,
    ).order_by(ConversationMessage.id.desc()).limit(1))
    unread = db.scalar(select(func.count()).select_from(ConversationMessage).where(
        ConversationMessage.conversation_id == conversation.id,
        ConversationMessage.sender_id != user.id,
        ConversationMessage.is_read.is_(False),
    )) or 0
    buyer_name = buyer.full_name if buyer else "Buyer"
    seller_name = seller.full_name if seller else "Seller"
    return ConversationRead(
        id=conversation.id, product_id=conversation.product_id,
        product_name=product.name if product else "Unavailable product",
        product_image_url=product.image_url if product else None,
        buyer_id=conversation.buyer_id, buyer_name=buyer_name,
        seller_id=conversation.seller_id, seller_name=seller_name,
        other_party_name=seller_name if user.id == conversation.buyer_id else buyer_name,
        status=conversation.status, last_message=last,
        updated_at=conversation.updated_at, unread_count=unread,
    )


def list_conversations(db: Session, user: User) -> list[ConversationRead]:
    if user.role not in (UserRole.BUYER, UserRole.SELLER):
        raise HTTPException(status_code=403, detail="Only buyers and sellers can access conversations.")
    field = Conversation.buyer_id if user.role == UserRole.BUYER else Conversation.seller_id
    rows = db.scalars(select(Conversation).where(field == user.id).order_by(
        Conversation.updated_at.desc(), Conversation.id.desc(),
    )).all()
    return [_summary(db, conversation, user) for conversation in rows]


def _add_message(db: Session, conversation: Conversation, sender: User, body: str) -> ConversationMessage:
    message = ConversationMessage(conversation_id=conversation.id, sender_id=sender.id, body=body)
    conversation.status = "open"
    conversation.updated_at = datetime.now(timezone.utc)
    recipient_id = conversation.seller_id if sender.id == conversation.buyer_id else conversation.buyer_id
    create_notification(db, user_id=recipient_id, kind="chat_message", title="New message",
        message=f"{sender.full_name} sent you a message about {db.get(Product, conversation.product_id).name if db.get(Product, conversation.product_id) else 'a product'}.",
        link=f"/messages/{conversation.id}")
    db.add(message)
    return message


def start_conversation(db: Session, buyer: User, details: StartConversation) -> ConversationDetail:
    if buyer.role != UserRole.BUYER:
        raise HTTPException(status_code=403, detail="Only buyers can start a conversation.")
    product = db.scalar(select(Product).where(
        Product.id == details.product_id, Product.is_active.is_(True),
    ))
    if product is None or product.seller_id is None:
        raise HTTPException(status_code=404, detail="This product does not have an active seller.")
    if product.seller_id == buyer.id:
        raise HTTPException(status_code=409, detail="You cannot message yourself about your own product.")
    seller = db.get(User, product.seller_id)
    if seller is None or UserRole.SELLER.value not in (seller.roles or [seller.role.value]) or not seller.is_active:
        raise HTTPException(status_code=409, detail="The seller is unavailable for messages.")
    conversation = db.scalar(select(Conversation).where(
        Conversation.buyer_id == buyer.id, Conversation.product_id == product.id,
    ).with_for_update())
    if conversation is None:
        conversation = Conversation(product_id=product.id, buyer_id=buyer.id, seller_id=seller.id, status="open")
        db.add(conversation)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            conversation = db.scalar(select(Conversation).where(
                Conversation.buyer_id == buyer.id, Conversation.product_id == product.id,
            ).with_for_update())
            if conversation is None:
                raise
    _add_message(db, conversation, buyer, details.body)
    db.commit()
    return get_conversation(db, conversation.id, buyer)


def get_conversation(db: Session, conversation_id: int, user: User) -> ConversationDetail:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    _ensure_participant(conversation, user)
    db.execute(update(ConversationMessage).where(
        ConversationMessage.conversation_id == conversation.id,
        ConversationMessage.sender_id != user.id,
        ConversationMessage.is_read.is_(False),
    ).values(is_read=True))
    db.execute(update(Notification).where(
        Notification.user_id == user.id,
        Notification.kind == "chat_message",
        Notification.link == f"/messages/{conversation.id}",
        Notification.is_read.is_(False),
    ).values(is_read=True))
    db.commit()
    summary = _summary(db, conversation, user)
    rows = db.execute(
        select(ConversationMessage, User.full_name)
        .join(User, User.id == ConversationMessage.sender_id)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(ConversationMessage.id.asc())
    ).all()
    messages = [MessageRead(
        id=message.id, sender_id=message.sender_id, sender_name=sender_name,
        body=message.body, is_read=message.is_read, created_at=message.created_at,
    ) for message, sender_name in rows]
    return ConversationDetail(**summary.model_dump(), messages=messages)


def send_message(db: Session, conversation_id: int, user: User, details: MessageCreate) -> ConversationDetail:
    conversation = db.scalar(select(Conversation).where(
        Conversation.id == conversation_id,
    ).with_for_update())
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    _ensure_participant(conversation, user)
    _add_message(db, conversation, user, details.body)
    db.commit()
    return get_conversation(db, conversation.id, user)


def update_status(db: Session, conversation_id: int, seller: User, next_status: str) -> ConversationRead:
    if seller.role != UserRole.SELLER:
        raise HTTPException(status_code=403, detail="Only the product seller can manage this conversation.")
    conversation = db.scalar(select(Conversation).where(
        Conversation.id == conversation_id,
    ).with_for_update())
    if conversation is None or conversation.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    conversation.status = next_status
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _summary(db, conversation, seller)


def unread_count(db: Session, user: User) -> int:
    if user.role not in (UserRole.BUYER, UserRole.SELLER):
        raise HTTPException(status_code=403, detail="Only buyers and sellers can access conversations.")
    field = Conversation.buyer_id if user.role == UserRole.BUYER else Conversation.seller_id
    return db.scalar(select(func.count()).select_from(ConversationMessage)
        .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
        .where(field == user.id, ConversationMessage.sender_id != user.id,
               ConversationMessage.is_read.is_(False))) or 0
