from typing import Optional, Dict, Any, List
from pydantic import conint, confloat
from app.schemas.base import BaseSchema
from app.models.puzzle import PuzzleDifficulty, PuzzleCategory

class PuzzleBase(BaseSchema):
    """Base puzzle schema"""
    title: str
    description: str
    category: PuzzleCategory
    difficulty: PuzzleDifficulty
    content: Dict[str, Any]
    points: conint(gt=0)
    time_limit: Optional[int] = None

class PuzzleCreate(PuzzleBase):
    """Schema for creating a new puzzle"""
    generation_params: Optional[Dict[str, Any]] = None

class PuzzleUpdate(BaseSchema):
    """Schema for updating puzzle details"""
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[PuzzleCategory] = None
    difficulty: Optional[PuzzleDifficulty] = None
    content: Optional[Dict[str, Any]] = None
    points: Optional[conint(gt=0)] = None
    time_limit: Optional[int] = None

class PuzzleInDB(PuzzleBase):
    """Schema for puzzle in database"""
    id: int
    creator_id: int
    times_solved: int
    average_solve_time: Optional[float]
    success_rate: confloat(ge=0, le=100)
    generation_params: Optional[Dict[str, Any]]

class PuzzleOut(PuzzleBase):
    """Schema for puzzle response"""
    id: int
    creator_id: int
    times_solved: int
    success_rate: confloat(ge=0, le=100)

class PuzzleAttemptCreate(BaseSchema):
    """Schema for creating a puzzle attempt"""
    solution_submitted: Dict[str, Any]
    time_taken: Optional[float]

class PuzzleAttemptOut(BaseSchema):
    """Schema for puzzle attempt response"""
    id: int
    user_id: int
    puzzle_id: int
    is_correct: bool
    time_taken: Optional[float]
    points_earned: Optional[int]

class PuzzleStats(BaseSchema):
    """Schema for puzzle statistics"""
    total_attempts: int
    success_rate: float
    average_time: Optional[float]
    fastest_solve: Optional[float]
    total_points_awarded: int

class LeaderboardEntry(BaseSchema):
    """Schema for leaderboard entry"""
    user_id: int
    username: str
    total_score: int
    rank: int
    rating: float
    puzzles_solved: int
    win_streak: int

class PuzzleRecommendation(BaseSchema):
    """Schema for puzzle recommendations"""
    puzzle_id: int
    title: str
    category: PuzzleCategory
    difficulty: PuzzleDifficulty
    points: int
    estimated_success_rate: float
    recommended_reason: str
