# Import necessary libraries
from fastapi import HTTPException, APIRouter
from fastapi.responses import ORJSONResponse
import mlflow
from geopy.distance import geodesic
import asyncio
import os
from sqlalchemy import select
import time
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

# Enable autologging
mlflow.sklearn.autolog()

# Load ML model
try:
    artifact_path = os.getenv("MLFLOW_ARTIFACT_PATH")
    model_uri = os.getenv("MLFLOW_URI")
    mlflow.set_tracking_uri(artifact_path)
    model = mlflow.sklearn.load_model(model_uri)
    logging.info(f"Model loaded from {model_uri}")
    print(f"Model loaded from {model_uri}")
except Exception as e:
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
    start_time = time.time()
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
    async with AsyncSessionLocal() as db:
        start_get_user_features = time.time()
        user = await db.execute(select(UserFeatures).filter(UserFeatures.user_id == user_id))
        user = user.scalar_one_or_none()
        finish_get_user_features = time.time() - start_get_user_features
        
        if not user:
            logging.error(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        # Inference user features to Nearest Neighbors model
        start_aggregate_user_features = time.time()
        user_features = np.array([getattr(user, f"feature_{i}") for i in range(1000)]).reshape(1, -1)
        finish_aggregate_user_features = time.time() - start_aggregate_user_features
        
        start_get_recommendations = time.time()
        difference, indices = model.kneighbors(user_features, n_neighbors=request.size)
        finish_get_recommendations = time.time() - start_get_recommendations
        # NOTE: Padding the indices need to be 4 digits rather than 5 (according to the example in assignment instruction). This is because the restaurant_id in the database is 4 digits.
        start_pad_indices = time.time()
        padded_array = [[f'{num:04}' for num in row] for row in indices]
        finish_pad_indices = time.time() - start_pad_indices

        # Calculate the displacement between user and restaurants
        start_calculate_displacement = time.time()
        restaurant_idx = [(f"r{idx}", diff) for idx, diff in zip(padded_array[0], difference[0])]
        # Extract restaurant ids
        restaurant_ids = np.array([r[0] for r in restaurant_idx])
        restaurants = await db.execute(select(Restaurant).filter(Restaurant.restaurant_id.in_(restaurant_ids)))
        restaurants = restaurants.scalars().all()
        restaurant_dict = {restaurant.restaurant_id: restaurant for restaurant in restaurants}
        
        recommended_restaurants = []
        for r_idx, diff in restaurant_idx:
            restaurant = restaurant_dict.get(r_idx)
            if restaurant:
                coords_user = (request.latitude, request.longitude)
                coords_restaurant = (restaurant.latitude, restaurant.longitude)
                displacement = int(geodesic(coords_user, coords_restaurant).m)
                if displacement <= int(request.max_dis):
                    recommended_restaurants.append(
                        Recommendation(
                            id=r_idx,
                            difference=round(float(diff), 1),
                            displacement=displacement
                        )
                    )
        finish_calculate_displacement = time.time() - start_calculate_displacement
        # Sort the recommended restaurants by displacement
        if bool(request.sort_dis):
            # Ascending order of displacement
            recommended_restaurants = sorted(recommended_restaurants, key=lambda x: x.displacement, reverse=False)
        else:
            # Ascending order of difference
            recommended_restaurants = sorted(recommended_restaurants, key=lambda x: x.difference, reverse=False)
            
        # Save prediction artifacts and request_params to the database
        # request_params
        start_insert_request_params = time.time()
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
        finish_insert_request_params = time.time() - start_insert_request_params
        
        # prediction_artifacts
        start_insert_prediction_artifacts = time.time()
        for recommendation in recommended_restaurants:
            db.add(PredictionArtifacts(
                request_id=str(new_request_id),
                restaurant_id=recommendation.id,
                difference=recommendation.difference,
                displacement=recommendation.displacement
            ))
        finish_insert_prediction_artifacts = time.time() - start_insert_prediction_artifacts
        await db.commit()
    
    # Return the top restaurants with difference and displacement
    logging.info(f"Recommended restaurants for user {user_id}")
    complete_time = time.time() - start_time
    print(f"Time to complete request: {complete_time}")
    print(f"Finished Get User Features Use {(finish_get_user_features/complete_time)*100}% of time")
    print(f"Finished Aggregate User Features Use {(finish_aggregate_user_features/complete_time)*100}% of time")
    print(f"Finished Get Recommendations Use {(finish_get_recommendations/complete_time)*100}% of time")
    print(f"Finished Pad Indices Use {(finish_pad_indices/complete_time)*100}% of time")
    print(f"Finished Calculate Displacement Use {(finish_calculate_displacement/complete_time)*100}% of time")
    print(f"Finished Insert Request Params Use {(finish_insert_request_params/complete_time)*100}% of time")
    print(f"Finished Insert Prediction Artifacts Use {(finish_insert_prediction_artifacts/complete_time)*100}% of time")

    return ORJSONResponse(content = RecommendationResponse(restaurants=recommended_restaurants).dict(), 
                        status_code=200)