from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, puzzles, payments, leaderboard, analytics

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(puzzles.router, prefix="/puzzles", tags=["Puzzles"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(leaderboard.router, prefix="/leaderboard", tags=["Leaderboard"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
