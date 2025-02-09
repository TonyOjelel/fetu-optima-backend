from typing import Optional
from pydantic import EmailStr, constr
from app.schemas.base import BaseSchema

class UserBase(BaseSchema):
    """Base user schema"""
    email: EmailStr
    username: constr(min_length=3, max_length=50)
    full_name: Optional[str] = None
    phone_number: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: constr(min_length=8)

class UserUpdate(BaseSchema):
    """Schema for updating user details"""
    email: Optional[EmailStr] = None
    username: Optional[constr(min_length=3, max_length=50)] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[constr(min_length=8)] = None

class UserInDB(UserBase):
    """Schema for user in database"""
    id: int
    is_active: bool
    is_superuser: bool
    two_factor_enabled: bool
    total_score: int
    rank: Optional[int]
    rating: float
    puzzles_solved: int
    win_streak: int
    wallet_balance: float
    total_earnings: float

class UserOut(UserBase):
    """Schema for user response"""
    id: int
    is_active: bool
    total_score: int
    rank: Optional[int]
    rating: float
    puzzles_solved: int
    win_streak: int

class Token(BaseSchema):
    """Schema for authentication token"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseSchema):
    """Schema for token payload"""
    user_id: int
    exp: int

class TwoFactorSetup(BaseSchema):
    """Schema for 2FA setup"""
    secret: str
    qr_code: str

class TwoFactorVerify(BaseSchema):
    """Schema for 2FA verification"""
    code: constr(min_length=6, max_length=6)  # 6-digit code
