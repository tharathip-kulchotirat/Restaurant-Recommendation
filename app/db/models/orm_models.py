from sqlalchemy import Column, Float, Integer, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import datetime
from app.db.setup_db import Base


class Restaurant(Base):
    __tablename__ = 'restaurants'

    restaurant_id = Column(String, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    
Restaurant.prediction_artifacts = relationship("PredictionArtifacts", back_populates="restaurant")

class UserFeatures(Base):
    __tablename__ = 'user_features'

    user_id = Column(String, primary_key=True)
    
    # Use a for loop to generate feature columns from feature_0 to feature_999
    for i in range(1000):
        locals()[f"feature_{i}"] = Column(Float)
        
UserFeatures.request_params = relationship("RequestParams", back_populates="user")

class RequestParams(Base):
    __tablename__ = 'request_params'

    request_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('user_features.user_id'))
    latitude = Column(Float)
    longitude = Column(Float)
    size = Column(Integer)
    max_dis = Column(Integer)
    sort_dis = Column(Integer)
    
    user = relationship("UserFeatures", back_populates="request_params")
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow())

class PredictionArtifacts(Base):
    __tablename__ = 'prediction_artifacts'

    id = Column(Integer, primary_key=True)
    request_id = Column(String, nullable=False)
    restaurant_id = Column(String, ForeignKey('restaurants.restaurant_id'), nullable=False)
    difference = Column(Float, nullable=False)
    displacement = Column(Integer, nullable=False)
        
    restaurant = relationship("Restaurant", back_populates="prediction_artifacts")

    created_at = Column(DateTime, default=datetime.datetime.utcnow())