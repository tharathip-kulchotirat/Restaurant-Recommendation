# Description: This file contains the main FastAPI application of the inference server.
#   The server is responsible for serving the recommendation API and the health check API.
#   The recommendation API is responsible for returning the top restaurants for a given user.
#   The health check API is responsible for returning the health status of the server.
#
# Machine Learning Model: Nearest Neighbors
#
# Responsible engineer: 
#   - Name: Tharathip Kuchotirat
#   - Email: tharathip.kul@gmail.com

# Import necessary libraries
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Logging
import logging
logging.basicConfig(filename='app.log', filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Init DB
from app.db.setup_db import init_db

# Initialize FastAPI application
app = FastAPI()

# Async initialization of the database
@app.on_event("startup")
async def startup_db():
    await init_db()

# Use CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check
@app.get("/healthcheck", tags=["health"])
async def healthcheck():
    """
    Performs a health check of the application.

    Returns:
        dict: A dictionary containing the status and message indicating the health of the application.
    """
    logging.info("Health check")
    return {"status": "OK", "message": "Application is healthy"}

# API Exception Handler
@app.exception_handler(Exception)
async def http_exception_handler(request, exc):
    """
    Handle HTTP exceptions and return a JSON response with a 500 status code and an error message.

    Parameters:
    - request: The incoming request object.
    - exc: The exception that was raised.

    Returns:
    - JSONResponse: A JSON response with a 500 status code and an error message.
    """
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"}
    )

# Import routers
from app.api.api_recommendation import router as recommendation_router

# Include routers
app.include_router(recommendation_router, tags=["/recommend"])