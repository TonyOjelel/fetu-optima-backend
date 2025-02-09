from sqlalchemy import Column, String, Integer, Float, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from app.models.base import BaseModel

class PuzzleDifficulty(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class PuzzleCategory(str, enum.Enum):
    LOGIC = "logic"
    MATH = "math"
    PATTERN = "pattern"
    WORD = "word"
    CODING = "coding"
    CRYPTOGRAPHY = "cryptography"

class Puzzle(BaseModel):
    """Puzzle model"""
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(Enum(PuzzleCategory), nullable=False)
    difficulty = Column(Enum(PuzzleDifficulty), nullable=False)
    
    # Puzzle content
    content = Column(JSON, nullable=False)  # Stores puzzle data, hints, and solution
    points = Column(Integer, nullable=False)
    time_limit = Column(Integer)  # Time limit in seconds, if applicable
    
    # AI generation metadata
    generation_params = Column(JSON, nullable=True)  # Parameters used for AI generation
    
    # Statistics
    times_solved = Column(Integer, default=0)
    average_solve_time = Column(Float, nullable=True)
    success_rate = Column(Float, default=0.0)
    
    # Relationships
    creator_id = Column(Integer, ForeignKey("user.id"))
    creator = relationship("User", back_populates="created_puzzles")
    attempts = relationship("PuzzleAttempt", back_populates="puzzle")

class PuzzleAttempt(BaseModel):
    """Records of puzzle attempts by users"""
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    puzzle_id = Column(Integer, ForeignKey("puzzle.id"), nullable=False)
    
    # Attempt details
    solution_submitted = Column(JSON, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_taken = Column(Float)  # Time taken in seconds
    points_earned = Column(Integer)
    
    # Relationships
    user = relationship("User", back_populates="puzzle_attempts")
    puzzle = relationship("Puzzle", back_populates="attempts")
