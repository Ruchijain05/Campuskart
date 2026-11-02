from pydantic import BaseModel, ConfigDict

from app.schemas.product import ProductRead


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recommended: list[ProductRead]
    popular: list[ProductRead]
    is_personalized: bool
