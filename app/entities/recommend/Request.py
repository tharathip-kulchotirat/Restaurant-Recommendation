from pydantic import BaseModel, Field

class RecommendationRequest(BaseModel):
    latitude: float
    longitude: float
    size: int | float = Field(..., gt=0)
    max_dis: int | float = Field(..., gt=0)
    sort_dis: int | float = Field(1, ge=0, le=1)