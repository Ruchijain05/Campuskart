from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.product import ProductRead
from app.schemas.recommendations import RecommendationRead
from app.services import recommendations as recommendation_service

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations", response_model=RecommendationRead)
def get_recommendations(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> RecommendationRead:
    recommended, popular, is_personalized = recommendation_service.recommendations_for_buyer(db, buyer.id)
    return RecommendationRead(
        recommended=recommended,
        popular=popular,
        is_personalized=is_personalized,
    )


@router.get("/recommendations/popular", response_model=list[ProductRead])
def get_popular_products(db: Session = Depends(get_db)) -> list[ProductRead]:
    return recommendation_service.popular_products(db)
