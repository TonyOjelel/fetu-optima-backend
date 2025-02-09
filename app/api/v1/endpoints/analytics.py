from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.cache import get_redis, CacheService
from app.services.analytics import AnalyticsService
from typing import Dict, Any

router = APIRouter()

@router.get("/user/stats")
async def get_user_statistics(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Get comprehensive statistics for the current user"""
    analytics = AnalyticsService(db, CacheService(redis))
    return await analytics.get_user_analytics(current_user.id)

@router.get("/user/{user_id}/performance")
async def get_user_performance(
    user_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Get performance analytics for a specific user"""
    # Check if the user has permission to view this data
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's data")
    
    analytics = AnalyticsService(db, CacheService(redis))
    return await analytics.get_user_analytics(user_id)

@router.get("/platform/overview")
async def get_platform_overview(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Get platform-wide analytics overview"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to view platform analytics")
    
    analytics = AnalyticsService(db, CacheService(redis))
    return await analytics.get_platform_analytics()

@router.get("/puzzles/performance")
async def get_puzzle_performance(
    category: Optional[PuzzleCategory] = None,
    difficulty: Optional[PuzzleDifficulty] = None,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Get performance analytics for puzzles"""
    cache = CacheService(redis)
    cache_key = f"puzzle_performance:{category}:{difficulty}"
    
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    query = db.query(PuzzleAttempt).join(Puzzle)
    
    if category:
        query = query.filter(Puzzle.category == category)
    if difficulty:
        query = query.filter(Puzzle.difficulty == difficulty)
    
    attempts = query.all()
    
    performance_data = {
        "total_attempts": len(attempts),
        "success_rate": len([a for a in attempts if a.is_correct]) / len(attempts) if attempts else 0,
        "average_time": sum(a.time_taken for a in attempts if a.time_taken) / len(attempts) if attempts else 0,
        "category_distribution": _get_category_distribution(attempts),
        "difficulty_distribution": _get_difficulty_distribution(attempts)
    }
    
    await cache.set(cache_key, performance_data, expire=3600)
    return performance_data

@router.get("/leaderboard/analytics")
async def get_leaderboard_analytics(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Get analytics for the leaderboard"""
    cache = CacheService(redis)
    cache_key = "leaderboard_analytics"
    
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    users = db.query(User).order_by(User.total_score.desc()).limit(100).all()
    
    analytics_data = {
        "score_distribution": _calculate_score_distribution(users),
        "rating_distribution": _calculate_rating_distribution(users),
        "top_performers": _get_top_performers(users),
        "recent_achievements": _get_recent_achievements(db)
    }
    
    await cache.set(cache_key, analytics_data, expire=3600)
    return analytics_data

def _get_category_distribution(attempts: List[PuzzleAttempt]) -> Dict[str, int]:
    """Calculate distribution of attempts across categories"""
    distribution = {}
    for attempt in attempts:
        category = attempt.puzzle.category
        distribution[category] = distribution.get(category, 0) + 1
    return distribution

def _get_difficulty_distribution(attempts: List[PuzzleAttempt]) -> Dict[str, int]:
    """Calculate distribution of attempts across difficulty levels"""
    distribution = {}
    for attempt in attempts:
        difficulty = attempt.puzzle.difficulty
        distribution[difficulty] = distribution.get(difficulty, 0) + 1
    return distribution

def _calculate_score_distribution(users: List[User]) -> Dict[str, int]:
    """Calculate distribution of user scores"""
    ranges = [(0, 1000), (1001, 5000), (5001, 10000), (10001, float('inf'))]
    distribution = {f"{r[0]}-{r[1]}": 0 for r in ranges}
    
    for user in users:
        for r in ranges:
            if r[0] <= user.total_score <= r[1]:
                distribution[f"{r[0]}-{r[1]}"] += 1
                break
    
    return distribution

def _calculate_rating_distribution(users: List[User]) -> Dict[str, int]:
    """Calculate distribution of user ratings"""
    ranges = [(0, 1200), (1201, 1500), (1501, 2000), (2001, float('inf'))]
    distribution = {f"{r[0]}-{r[1]}": 0 for r in ranges}
    
    for user in users:
        for r in ranges:
            if r[0] <= user.rating <= r[1]:
                distribution[f"{r[0]}-{r[1]}"] += 1
                break
    
    return distribution

def _get_top_performers(users: List[User], limit: int = 10) -> List[Dict[str, Any]]:
    """Get details of top performing users"""
    return [{
        "id": user.id,
        "username": user.username,
        "total_score": user.total_score,
        "rating": user.rating,
        "puzzles_solved": user.puzzles_solved,
        "win_streak": user.win_streak
    } for user in users[:limit]]

def _get_recent_achievements(db: Session) -> List[Dict[str, Any]]:
    """Get recent notable achievements"""
    # Query for recent high scores, long win streaks, etc.
    achievements = []
    
    # High scores
    high_scores = db.query(PuzzleAttempt).filter(
        PuzzleAttempt.is_correct == True
    ).order_by(PuzzleAttempt.points_earned.desc()).limit(5).all()
    
    for score in high_scores:
        achievements.append({
            "type": "high_score",
            "user_id": score.user_id,
            "points": score.points_earned,
            "puzzle_id": score.puzzle_id,
            "timestamp": score.created_at
        })
    
    # Win streaks
    win_streaks = db.query(User).order_by(User.win_streak.desc()).limit(5).all()
    for user in win_streaks:
        if user.win_streak >= 5:  # Only include significant streaks
            achievements.append({
                "type": "win_streak",
                "user_id": user.id,
                "streak": user.win_streak,
                "timestamp": datetime.utcnow()
            })
    
    return sorted(achievements, key=lambda x: x["timestamp"], reverse=True)
