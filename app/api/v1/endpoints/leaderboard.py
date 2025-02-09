from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.cache import get_redis, CacheService
from app.schemas.puzzle import LeaderboardEntry
from app.models.user import User
from app.websockets.server import ConnectionManager

router = APIRouter()
manager = ConnectionManager()

@router.get("/global", response_model=List[LeaderboardEntry])
async def get_global_leaderboard(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Get global leaderboard"""
    cache = CacheService(redis)
    cache_key = f"global_leaderboard:{skip}:{limit}"
    
    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Query database
    users = db.query(User).order_by(
        User.total_score.desc()
    ).offset(skip).limit(limit).all()
    
    # Prepare leaderboard entries
    leaderboard = []
    for rank, user in enumerate(users, start=skip + 1):
        leaderboard.append({
            "user_id": user.id,
            "username": user.username,
            "total_score": user.total_score,
            "rank": rank,
            "rating": user.rating,
            "puzzles_solved": user.puzzles_solved,
            "win_streak": user.win_streak
        })
    
    # Cache results
    await cache.set(cache_key, leaderboard, expire=300)  # Cache for 5 minutes
    return leaderboard

@router.get("/category/{category}", response_model=List[LeaderboardEntry])
async def get_category_leaderboard(
    category: PuzzleCategory,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Get category-specific leaderboard"""
    cache = CacheService(redis)
    cache_key = f"category_leaderboard:{category}:{skip}:{limit}"
    
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Query users with their performance in specific category
    category_scores = db.query(
        User,
        func.count(PuzzleAttempt.id).label('puzzles_solved'),
        func.sum(PuzzleAttempt.points_earned).label('category_score')
    ).join(
        PuzzleAttempt
    ).join(
        Puzzle
    ).filter(
        Puzzle.category == category,
        PuzzleAttempt.is_correct == True
    ).group_by(
        User.id
    ).order_by(
        text('category_score DESC')
    ).offset(skip).limit(limit).all()
    
    leaderboard = []
    for rank, (user, solved, score) in enumerate(category_scores, start=skip + 1):
        leaderboard.append({
            "user_id": user.id,
            "username": user.username,
            "total_score": score or 0,
            "rank": rank,
            "rating": user.rating,
            "puzzles_solved": solved,
            "win_streak": user.win_streak
        })
    
    await cache.set(cache_key, leaderboard, expire=300)
    return leaderboard

@router.websocket("/ws/live")
async def leaderboard_websocket(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """WebSocket endpoint for real-time leaderboard updates"""
    try:
        # Authenticate user
        user = await get_current_user(token)
        
        # Accept connection
        await manager.connect(websocket, user.id, "leaderboard")
        
        # Send initial leaderboard data
        cache = CacheService(redis)
        initial_data = await cache.get("global_leaderboard:0:100")
        if initial_data:
            await websocket.send_json({
                "type": "initial_data",
                "data": initial_data
            })
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message["type"] == "subscribe_category":
                    category = message.get("category")
                    if category:
                        await manager.subscribe_to_channel(
                            user.id,
                            f"leaderboard_category_{category}"
                        )
                        
                        # Send initial category data
                        category_data = await cache.get(f"category_leaderboard:{category}:0:100")
                        if category_data:
                            await websocket.send_json({
                                "type": "category_data",
                                "category": category,
                                "data": category_data
                            })
                
        except WebSocketDisconnect:
            await manager.disconnect(websocket, user.id)
            
    except Exception as e:
        await websocket.close(code=4000, reason=str(e))

async def update_leaderboard(
    user_id: int,
    points: int,
    category: Optional[str] = None,
    redis: Redis = None
):
    """Update leaderboard and notify connected clients"""
    cache = CacheService(redis)
    
    # Update global leaderboard score
    await cache.increment(f"user_score:{user_id}", points)
    
    # Update category score if specified
    if category:
        await cache.increment(f"user_category_score:{category}:{user_id}", points)
    
    # Invalidate cached leaderboards
    await cache.delete("global_leaderboard:*")
    if category:
        await cache.delete(f"category_leaderboard:{category}:*")
    
    # Notify connected clients
    user_data = await get_user_leaderboard_data(user_id, redis)
    
    await manager.broadcast({
        "type": "score_update",
        "data": user_data
    }, "leaderboard")
    
    if category:
        await manager.broadcast({
            "type": "category_update",
            "category": category,
            "data": user_data
        }, f"leaderboard_category_{category}")

async def get_user_leaderboard_data(user_id: int, redis: Redis) -> dict:
    """Get user's current leaderboard data"""
    cache = CacheService(redis)
    
    # Get user's current score and rank
    score = await cache.get(f"user_score:{user_id}")
    rank = await cache.get_sorted_set_rank("leaderboard", str(user_id))
    
    return {
        "user_id": user_id,
        "score": int(score) if score else 0,
        "rank": rank + 1 if rank is not None else None
    }
