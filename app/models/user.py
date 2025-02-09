from sqlalchemy import Column, String, Boolean, Integer, Float
from app.models.base import BaseModel

class User(BaseModel):
    """User model"""
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # 2FA
    two_factor_secret = Column(String, nullable=True)
    two_factor_enabled = Column(Boolean, default=False)
    
    # Game stats
    total_score = Column(Integer, default=0)
    rank = Column(Integer)
    rating = Column(Float, default=1500.0)  # ELO rating
    puzzles_solved = Column(Integer, default=0)
    win_streak = Column(Integer, default=0)
    
    # Mobile Money
    phone_number = Column(String, nullable=True)
    wallet_balance = Column(Float, default=0.0)
    total_earnings = Column(Float, default=0.0)
