from pydantic import BaseModel
from typing import Optional
from typing import List

class Anime(BaseModel):
    id: int
    name: str
    genre: Optional[str] = None
    episodes: Optional[int] = None
    type: Optional[str] = None
    rating: Optional[float] = None
    members: Optional[int] = None
    image_url: Optional[str] = None


class AnimeSummaryResponse(BaseModel):
    anime_id: Optional[int] = None
    title: str
    summary: str
    source: str


class Recommendation(BaseModel):
    user_id: int
    anime_id: int
    score: float


class TitleRecommendation(BaseModel):
    title: str
    score: Optional[float] = None
    anime_id: Optional[int] = None
    image_url: Optional[str] = None


class TitleRecommendationResponse(BaseModel):
    query_title: str
    recommendations: List[TitleRecommendation]


class AuthRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str


class AuthResponse(BaseModel):
    user: UserResponse


class FavoriteRequest(BaseModel):
    anime_id: int


class FavoriteItem(BaseModel):
    anime_id: int
    title: str
    image_url: Optional[str] = None


class FavoritesResponse(BaseModel):
    user_id: int
    favorites: List[FavoriteItem]


class UserSimilarityRecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[TitleRecommendation]

class Health(BaseModel):
    status: str = "ok"
