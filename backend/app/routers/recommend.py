from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas import (
    TitleRecommendation,
    TitleRecommendationResponse,
    UserSimilarityRecommendationResponse,
)
from backend.app.services.recommender import TitleSimilarityRecommender
from backend.app.services.user_similarity import UserSimilarityRecommender

router = APIRouter(prefix="/recommend", tags=["recommend"])

RECOMMENDER: TitleSimilarityRecommender | None = None
USER_RECOMMENDER: UserSimilarityRecommender | None = None


@router.get("/", response_model=TitleRecommendationResponse)
def recommend_by_title(
    title: str = Query(..., min_length=1, description="Anime title input from the user"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> TitleRecommendationResponse:
    if RECOMMENDER is None:
        raise HTTPException(status_code=503, detail="Recommender not ready")
    try:
        recommendations = RECOMMENDER.recommend_by_title(title=title, limit=limit, offset=offset)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Anime title not found in dataset: {title}",
        ) from None
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TitleRecommendationResponse(
        query_title=title,
        recommendations=[TitleRecommendation(**item) for item in recommendations],
    )


@router.get("/user/{user_id}", response_model=UserSimilarityRecommendationResponse)
def recommend_by_user_similarity(
    user_id: int,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> UserSimilarityRecommendationResponse:
    if USER_RECOMMENDER is None:
        raise HTTPException(status_code=503, detail="User similarity recommender not ready")
    recommendations = USER_RECOMMENDER.recommend_for_user(user_id=user_id, limit=limit, offset=offset)
    return UserSimilarityRecommendationResponse(
        user_id=user_id,
        recommendations=[TitleRecommendation(**item) for item in recommendations],
    )
