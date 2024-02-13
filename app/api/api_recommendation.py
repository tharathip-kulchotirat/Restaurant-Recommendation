# Import necessary libraries
from fastapi import HTTPException, APIRouter
from fastapi.responses import ORJSONResponse
import mlflow
from geopy.distance import geodesic
import os
# NEW: import sqlalchemy
from sqlalchemy import select, func, cast, Float
# END NEW

import numpy as np

# for generating request_id
import uuid

# API Models
from app.entities.recommend.Request import RecommendationRequest
from app.entities.recommend.Response import RecommendationResponse, Recommendation

# Data Models
from app.db.models.orm_models import UserFeatures, Restaurant, RequestParams, PredictionArtifacts

# Database setup
from app.db.setup_db import AsyncSessionLocal

# Logging
import logging
logging.basicConfig(filename='app.log', filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set up MLflow Model
try:
    mlflow.set_tracking_uri(os.getenv("MLFLOW_URI"))
    model = None
    
    # In dev environment, load the model from the local file system
    if os.getenv("ENV") == "dev":
        
        # Get Run ID
        runs = mlflow.search_runs(experiment_ids=[0])
        
        if runs.empty:
            logging.error("No runs found")
            raise HTTPException(status_code=500, detail="No runs found")
        else:
            model = mlflow.sklearn.load_model("runs:/" + runs.iloc[0, :]['run_id'] + "/recommend")
        
    # In prod environment, load the model from MLflow model registry
    else:
        artifact_path = os.getenv("MLFLOW_ARTIFACT_PATH")
        model = mlflow.sklearn.load_model(artifact_path)
        
    model.set_params(n_jobs = -1, algorithm='auto', leaf_size=400)
except Exception as e:
    print(e)
    logging.error(f"Error loading model: {e}")
    raise HTTPException(status_code=500, detail="Please provide a valid MLflow URI.")

# Router
router = APIRouter()

@router.get("/recommend/{user_id}", response_model=RecommendationResponse)
async def recommend(
    user_id: str, 
    latitude: float, 
    longitude: float, 
    size: int | float = 20, 
    max_dis: int | float = 5000, 
    sort_dis: int | float = 1
) -> RecommendationResponse:
    """
    Recommends restaurants based on user's location and preferences.

    Args:
        user_id (str): The ID of the user.
        latitude (float): The latitude of the user's location.
        longitude (float): The longitude of the user's location.
        size (int, optional): The number of restaurants to recommend. Defaults to 20.
        max_dis (int, optional): The maximum distance (in meters) from the user's location to consider for recommendations. Defaults to 5000.
        sort_dis (int, optional): Flag to indicate whether to sort the recommendations by distance. 1 for sorting, 0 for not sorting. Defaults to 1.

    Returns:
        List[Restaurant]: A list of recommended restaurants.

    Raises:
        HTTPException: If there is an error parsing the request.

    """
    try:
        request = RecommendationRequest(
            latitude=latitude,
            longitude=longitude,
            size=size,
            max_dis=max_dis,
            sort_dis=sort_dis
        )
    except Exception as e:
        logging.error(f"Error parsing request: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request. Error parsing request: {e}")
    
    # Get user features from the database
    db = AsyncSessionLocal()
    # async with AsyncSessionLocal() as db:
    user = await db.execute(select(UserFeatures).filter(UserFeatures.user_id == user_id))
    user = user.scalar_one_or_none()
    
    if not user:
        logging.error(f"User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    # Inference user features to Nearest Neighbors model
    user_features = np.array([getattr(user, f"feature_{i}") for i in range(1000)]).reshape(1, -1)
    
    # NEW: EDIT get restaurants that are within the max_dis
    # install `brew install postgis` first, then...
    # SQL: CREATE EXTENSION postgis;
    # SQL: SELECT PostGIS_Version();
    restaurants = await db.execute(select(Restaurant.restaurant_id, Restaurant.latitude, Restaurant.longitude)
                                    .filter(
                                        func.ST_DistanceSphere(
                                            func.ST_MakePoint(request.latitude, request.longitude),
                                            func.ST_MakePoint(Restaurant.latitude, Restaurant.longitude)
                                        ) <= float(request.max_dis)
                                    ))
    restaurants = restaurants.all()
    restaurants = [(row[0], int(geodesic((request.latitude,request.longitude), (row[1], row[2])).meters)) for row in restaurants if int(geodesic((request.latitude,request.longitude), (row[1], row[2])).meters) <= request.max_dis]
    # END NEW
    
    # NEW: find nn from len of restaurant_ids
    difference, indices = model.kneighbors(user_features, n_neighbors=len(restaurants))
    sorted_nn = sorted(zip(difference[0], indices[0]), key=lambda x: x[0])
    indices = [idx for _, idx in sorted_nn]
    difference = [diff for diff, _ in sorted_nn]
    # END NEW
    
    # NOTE: Padding the indices need to be 4 digits rather than 5 (according to the example in assignment instruction). This is because the restaurant_id in the database is 4 digits.
    padded_array = [f'{row:04}' for row in indices]

    # Calculate the displacement between user and restaurants
    restaurant_idx = [(f"r{idx}", diff) for idx, diff in zip(padded_array, difference)]
    
    # NEW
    recommended_restaurants = []
    for r_idx, diff in restaurant_idx:
        ids = [x[1] for x in restaurants if x[0] == r_idx]
        if len(ids) > 0:
            recommended_restaurants.append(
                Recommendation(
                    id=r_idx,
                    difference=round(float(diff), 1),
                    displacement=ids[0]
                )
        )
    # END NEW
    
    # # Sort the recommended restaurants by displacement
    if bool(request.sort_dis):
        # Ascending order of displacement
        recommended_restaurants = sorted(recommended_restaurants, key=lambda x: x.displacement, reverse=False)
    else:
        # Ascending order of difference
        recommended_restaurants = sorted(recommended_restaurants, key=lambda x: x.difference, reverse=False)
    
        
    # Save prediction artifacts and request_params to the database
    # request_params
    new_request_id = uuid.uuid4()
    request_params = RequestParams(
        request_id=str(new_request_id),
        user_id=user_id,
        latitude=request.latitude,
        longitude=request.longitude,
        size=request.size,
        max_dis=request.max_dis,
        sort_dis=request.sort_dis
    )
    db.add(request_params)
    
    # prediction_artifacts
    for recommendation in recommended_restaurants:
        db.add(PredictionArtifacts(
            request_id=str(new_request_id),
            restaurant_id=recommendation.id,
            difference=recommendation.difference,
            displacement=recommendation.displacement
        ))
    await db.commit()
    
    # Return the top restaurants with difference and displacement
    logging.info(f"Recommended restaurants for user {user_id}")

    return ORJSONResponse(content = RecommendationResponse(restaurants=recommended_restaurants).dict(), 
                        status_code=200)