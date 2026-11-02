from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.models.auth import User
from app.schemas.conversations import ConversationDetail, ConversationRead, ConversationStatusUpdate, MessageCreate, StartConversation
from app.services import conversations as conversation_service

router = APIRouter(prefix="/conversations", tags=["buyer-seller chat"])


@router.get("", response_model=list[ConversationRead])
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ConversationRead]:
    return conversation_service.list_conversations(db, user)


@router.get("/unread-count")
def get_unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, int]:
    return {"unread_count": conversation_service.unread_count(db, user)}


@router.post("", response_model=ConversationDetail, status_code=201)
def start_conversation(details: StartConversation, db: Session = Depends(get_db), buyer: User = Depends(get_current_user)) -> ConversationDetail:
    return conversation_service.start_conversation(db, buyer, details)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ConversationDetail:
    return conversation_service.get_conversation(db, conversation_id, user)


@router.post("/{conversation_id}/messages", response_model=ConversationDetail)
def send_message(conversation_id: int, details: MessageCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ConversationDetail:
    return conversation_service.send_message(db, conversation_id, user, details)


@router.patch("/{conversation_id}/status", response_model=ConversationRead)
def update_conversation_status(conversation_id: int, details: ConversationStatusUpdate, db: Session = Depends(get_db), seller: User = Depends(get_current_user)) -> ConversationRead:
    return conversation_service.update_status(db, conversation_id, seller, details.status.value)
