from pydantic import BaseModel
from typing import Optional, List, Dict, Union

class Recommendation(BaseModel):
    id: str # restaurant_id
    difference: float # euclidean distance
    displacement: int # H3 index

class RecommendationResponse(BaseModel):
    restaurants: List[Recommendation]