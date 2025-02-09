from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.puzzle import (
    PuzzleCreate, PuzzleOut, PuzzleUpdate, PuzzleAttemptCreate,
    PuzzleAttemptOut, PuzzleStats, PuzzleRecommendation
)
from app.services.ai_puzzle import AIPuzzleGenerator, PuzzleValidator
from app.models.puzzle import Puzzle, PuzzleAttempt
from app.core.cache import get_redis, CacheService

router = APIRouter()
puzzle_generator = AIPuzzleGenerator()

@router.post("/generate", response_model=PuzzleOut)
async def generate_puzzle(
    category: PuzzleCategory,
    difficulty: PuzzleDifficulty,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new AI puzzle"""
    # Get user's skill level
    user_skill_level = current_user.rating / 3000  # Normalize rating to 0-1

    # Generate puzzle
    puzzle_data = await puzzle_generator.generate_puzzle(
        category=category,
        difficulty=difficulty,
        user_skill_level=user_skill_level
    )

    # Create puzzle in database
    puzzle = Puzzle(
        title=puzzle_data["title"],
        description=puzzle_data["question"],
        category=category,
        difficulty=difficulty,
        content=puzzle_data,
        points=calculate_points(difficulty),
        creator_id=current_user.id
    )
    db.add(puzzle)
    db.commit()
    db.refresh(puzzle)
    return puzzle

@router.post("/{puzzle_id}/attempt", response_model=PuzzleAttemptOut)
async def submit_attempt(
    puzzle_id: int,
    attempt: PuzzleAttemptCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Submit a puzzle attempt"""
    puzzle = db.query(Puzzle).filter(Puzzle.id == puzzle_id).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")

    # Validate solution
    is_correct = PuzzleValidator.validate_solution(
        puzzle.category,
        attempt.solution_submitted,
        puzzle.content["solution"]
    )

    # Create attempt record
    puzzle_attempt = PuzzleAttempt(
        user_id=current_user.id,
        puzzle_id=puzzle_id,
        solution_submitted=attempt.solution_submitted,
        is_correct=is_correct,
        time_taken=attempt.time_taken,
        points_earned=puzzle.points if is_correct else 0
    )
    db.add(puzzle_attempt)

    if is_correct:
        # Update user stats
        current_user.total_score += puzzle.points
        current_user.puzzles_solved += 1
        current_user.win_streak += 1

        # Update puzzle stats
        puzzle.times_solved += 1
        puzzle.success_rate = (puzzle.times_solved / (puzzle.attempts.count() + 1)) * 100

        # Schedule background task to update leaderboard
        background_tasks.add_task(
            update_leaderboard,
            user_id=current_user.id,
            points=puzzle.points,
            redis=redis
        )

    else:
        current_user.win_streak = 0

    db.commit()
    db.refresh(puzzle_attempt)
    return puzzle_attempt

@router.get("/recommendations", response_model=List[PuzzleRecommendation])
async def get_recommendations(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized puzzle recommendations"""
    # Get user's recent attempts
    recent_attempts = db.query(PuzzleAttempt).filter(
        PuzzleAttempt.user_id == current_user.id
    ).order_by(PuzzleAttempt.created_at.desc()).limit(10).all()

    # Calculate success rate per category
    category_stats = calculate_category_stats(recent_attempts)

    # Get recommended puzzles
    recommendations = []
    for category, stats in category_stats.items():
        # Adjust difficulty based on performance
        recommended_difficulty = await puzzle_generator.adjust_difficulty(
            success_rate=stats["success_rate"],
            current_difficulty=stats["current_difficulty"]
        )

        # Find suitable puzzles
        suitable_puzzles = db.query(Puzzle).filter(
            Puzzle.category == category,
            Puzzle.difficulty == get_difficulty_level(recommended_difficulty)
        ).limit(2).all()

        recommendations.extend(suitable_puzzles)

    return [create_recommendation(puzzle, category_stats) for puzzle in recommendations]

@router.get("/{puzzle_id}/stats", response_model=PuzzleStats)
async def get_puzzle_stats(
    puzzle_id: int,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Get statistics for a specific puzzle"""
    # Try to get from cache first
    cache = CacheService(redis)
    cache_key = f"puzzle_stats:{puzzle_id}"
    stats = await cache.get(cache_key)

    if not stats:
        # Calculate stats from database
        puzzle = db.query(Puzzle).filter(Puzzle.id == puzzle_id).first()
        if not puzzle:
            raise HTTPException(status_code=404, detail="Puzzle not found")

        attempts = puzzle.attempts
        total_attempts = len(attempts)
        success_rate = puzzle.success_rate
        average_time = sum(a.time_taken for a in attempts if a.time_taken) / total_attempts if total_attempts > 0 else 0
        fastest_solve = min((a.time_taken for a in attempts if a.time_taken), default=None)
        total_points = sum(a.points_earned for a in attempts)

        stats = {
            "total_attempts": total_attempts,
            "success_rate": success_rate,
            "average_time": average_time,
            "fastest_solve": fastest_solve,
            "total_points_awarded": total_points
        }

        # Cache the results
        await cache.set(cache_key, stats, expire=3600)

    return stats

def calculate_points(difficulty: PuzzleDifficulty) -> int:
    """Calculate points based on difficulty"""
    points_map = {
        PuzzleDifficulty.BEGINNER: 100,
        PuzzleDifficulty.INTERMEDIATE: 250,
        PuzzleDifficulty.ADVANCED: 500,
        PuzzleDifficulty.EXPERT: 1000
    }
    return points_map[difficulty]

async def update_leaderboard(user_id: int, points: int, redis: Redis):
    """Update user's score in the leaderboard"""
    cache = CacheService(redis)
    await cache.increment(f"user_score:{user_id}", points)
    await cache.add_to_sorted_set("leaderboard", points, str(user_id))
