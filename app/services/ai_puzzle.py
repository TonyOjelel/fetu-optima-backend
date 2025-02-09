import openai
from typing import Dict, Any, List
from app.core.config import settings
from app.models.puzzle import PuzzleDifficulty, PuzzleCategory

class AIPuzzleGenerator:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY

    async def generate_puzzle(
        self,
        category: PuzzleCategory,
        difficulty: PuzzleDifficulty,
        user_skill_level: float
    ) -> Dict[str, Any]:
        """Generate a puzzle using OpenAI"""
        
        # Create prompt based on category and difficulty
        prompt = self._create_prompt(category, difficulty, user_skill_level)
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert puzzle creator for the FETU Optima platform."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        # Parse and structure the response
        puzzle_data = self._parse_response(response.choices[0].message.content)
        return puzzle_data

    def _create_prompt(
        self,
        category: PuzzleCategory,
        difficulty: PuzzleDifficulty,
        user_skill_level: float
    ) -> str:
        """Create appropriate prompt based on parameters"""
        prompts = {
            PuzzleCategory.LOGIC: "Create a logic puzzle that requires deductive reasoning",
            PuzzleCategory.MATH: "Create a mathematical problem that involves {difficulty} concepts",
            PuzzleCategory.PATTERN: "Create a pattern recognition puzzle with increasing complexity",
            PuzzleCategory.WORD: "Create a word puzzle that tests vocabulary and language skills",
            PuzzleCategory.CODING: "Create a coding challenge that tests algorithmic thinking",
            PuzzleCategory.CRYPTOGRAPHY: "Create a cryptographic puzzle with encoded messages"
        }

        difficulty_modifiers = {
            PuzzleDifficulty.BEGINNER: "basic",
            PuzzleDifficulty.INTERMEDIATE: "intermediate",
            PuzzleDifficulty.ADVANCED: "advanced",
            PuzzleDifficulty.EXPERT: "expert"
        }

        base_prompt = prompts[category].format(difficulty=difficulty_modifiers[difficulty])
        return f"{base_prompt}. User skill level: {user_skill_level}. Include question, hints, solution, and explanation."

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse and structure the AI response into puzzle format"""
        # Implementation would parse the AI response into structured format
        # This is a simplified version
        return {
            "question": response.split("Question:")[1].split("Hints:")[0].strip(),
            "hints": response.split("Hints:")[1].split("Solution:")[0].strip().split("\n"),
            "solution": response.split("Solution:")[1].split("Explanation:")[0].strip(),
            "explanation": response.split("Explanation:")[1].strip()
        }

    async def adjust_difficulty(
        self,
        success_rate: float,
        current_difficulty: float,
        target_success_rate: float = 0.7
    ) -> float:
        """Adjust puzzle difficulty based on user performance"""
        difficulty_delta = (target_success_rate - success_rate) * 0.1
        return max(0.1, min(1.0, current_difficulty + difficulty_delta))

class PuzzleValidator:
    @staticmethod
    def validate_solution(puzzle_type: str, submitted_solution: Any, correct_solution: Any) -> bool:
        """Validate user's solution against correct solution"""
        if puzzle_type == "coding":
            return PuzzleValidator._validate_coding_solution(submitted_solution, correct_solution)
        elif puzzle_type == "math":
            return PuzzleValidator._validate_math_solution(submitted_solution, correct_solution)
        # Add more validation methods for different puzzle types
        return submitted_solution == correct_solution

    @staticmethod
    def _validate_coding_solution(submitted_code: str, test_cases: List[Dict[str, Any]]) -> bool:
        """Validate coding solution using test cases"""
        # Implementation would run submitted code against test cases
        # This is a placeholder
        return True

    @staticmethod
    def _validate_math_solution(submitted_answer: float, correct_answer: float, tolerance: float = 0.001) -> bool:
        """Validate mathematical solution with tolerance"""
        return abs(submitted_answer - correct_answer) < tolerance
