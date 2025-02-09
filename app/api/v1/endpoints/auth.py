from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings
from app.schemas.user import UserCreate, Token, UserOut, TwoFactorSetup, TwoFactorVerify
from app.core.database import get_db

router = APIRouter()

@router.post("/signup", response_model=UserOut)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create new user"""
    # Check if user exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login user"""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if 2FA is enabled
    if user.two_factor_enabled:
        # Return temporary token for 2FA verification
        access_token = create_access_token(
            data={"sub": str(user.id), "temp": True},
            expires_delta=timedelta(minutes=5)
        )
        return {"access_token": access_token, "token_type": "bearer", "requires_2fa": True}
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/2fa/setup", response_model=TwoFactorSetup)
async def setup_2fa(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Setup 2FA for user"""
    # Generate secret
    secret = SecurityService.generate_2fa_secret()
    
    # Update user
    user = db.query(User).filter(User.id == current_user.id).first()
    user.two_factor_secret = secret
    db.commit()
    
    # Generate QR code
    qr_code = SecurityService.generate_2fa_qr_code(secret, user.email)
    
    return {"secret": secret, "qr_code": qr_code}

@router.post("/2fa/verify", response_model=Token)
async def verify_2fa(
    verification: TwoFactorVerify,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify 2FA code"""
    user = db.query(User).filter(User.id == current_user.id).first()
    
    if not SecurityService.verify_2fa_code(user.two_factor_secret, verification.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code"
        )
    
    # Enable 2FA for user
    user.two_factor_enabled = True
    db.commit()
    
    # Create full access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}
