from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Dict, List, Any
from app.models.puzzle import Puzzle, PuzzleAttempt, PuzzleCategory, PuzzleDifficulty
from app.models.user import User
from app.models.transaction import Transaction, TransactionStatus
from app.core.cache import CacheService

class AnalyticsService:
    def __init__(self, db: Session, cache: CacheService):
        self.db = db
        self.cache = cache

    async def get_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive analytics for a user"""
        cache_key = f"user_analytics:{user_id}"
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # Get user's puzzle attempts
        attempts = self.db.query(PuzzleAttempt).filter(
            PuzzleAttempt.user_id == user_id
        ).all()

        # Calculate statistics
        total_attempts = len(attempts)
        successful_attempts = len([a for a in attempts if a.is_correct])
        success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0

        # Category performance
        category_stats = {}
        for category in PuzzleCategory:
            category_attempts = [a for a in attempts if a.puzzle.category == category]
            if category_attempts:
                category_success = len([a for a in category_attempts if a.is_correct])
                category_stats[category] = {
                    "attempts": len(category_attempts),
                    "success_rate": (category_success / len(category_attempts) * 100),
                    "average_time": sum(a.time_taken for a in category_attempts if a.time_taken) / len(category_attempts)
                }

        # Time-based analysis
        time_stats = self._calculate_time_stats(attempts)

        analytics_data = {
            "total_attempts": total_attempts,
            "successful_attempts": successful_attempts,
            "overall_success_rate": success_rate,
            "category_performance": category_stats,
            "time_analysis": time_stats,
            "skill_progression": self._calculate_skill_progression(attempts),
            "engagement_metrics": self._calculate_engagement_metrics(user_id)
        }

        # Cache the results
        await self.cache.set(cache_key, analytics_data, expire=3600)
        return analytics_data

    async def get_platform_analytics(self) -> Dict[str, Any]:
        """Get platform-wide analytics"""
        cache_key = "platform_analytics"
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # User statistics
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active == True).count()

        # Puzzle statistics
        puzzle_stats = self._calculate_puzzle_stats()

        # Payment statistics
        payment_stats = self._calculate_payment_stats()

        # Engagement metrics
        engagement_metrics = self._calculate_platform_engagement()

        platform_data = {
            "user_stats": {
                "total_users": total_users,
                "active_users": active_users,
                "user_growth": self._calculate_user_growth()
            },
            "puzzle_stats": puzzle_stats,
            "payment_stats": payment_stats,
            "engagement_metrics": engagement_metrics
        }

        # Cache the results
        await self.cache.set(cache_key, platform_data, expire=3600)
        return platform_data

    def _calculate_time_stats(self, attempts: List[PuzzleAttempt]) -> Dict[str, Any]:
        """Calculate time-based statistics"""
        if not attempts:
            return {}

        # Group attempts by hour
        hour_distribution = {}
        for attempt in attempts:
            hour = attempt.created_at.hour
            hour_distribution[hour] = hour_distribution.get(hour, 0) + 1

        # Calculate peak hours
        peak_hour = max(hour_distribution.items(), key=lambda x: x[1])[0]

        return {
            "peak_activity_hour": peak_hour,
            "hourly_distribution": hour_distribution,
            "average_session_length": self._calculate_average_session_length(attempts)
        }

    def _calculate_skill_progression(self, attempts: List[PuzzleAttempt]) -> Dict[str, Any]:
        """Calculate user's skill progression"""
        if not attempts:
            return {}

        # Sort attempts by date
        sorted_attempts = sorted(attempts, key=lambda x: x.created_at)
        
        # Calculate moving success rate
        window_size = 10
        success_rates = []
        for i in range(0, len(sorted_attempts), window_size):
            window = sorted_attempts[i:i+window_size]
            success_rate = len([a for a in window if a.is_correct]) / len(window)
            success_rates.append(success_rate)

        return {
            "success_rate_progression": success_rates,
            "difficulty_progression": self._calculate_difficulty_progression(sorted_attempts)
        }

    def _calculate_engagement_metrics(self, user_id: int) -> Dict[str, Any]:
        """Calculate user engagement metrics"""
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)

        # Get recent activity
        recent_attempts = self.db.query(PuzzleAttempt).filter(
            PuzzleAttempt.user_id == user_id,
            PuzzleAttempt.created_at >= thirty_days_ago
        ).all()

        # Calculate daily activity
        daily_activity = {}
        for attempt in recent_attempts:
            day = attempt.created_at.date()
            daily_activity[day] = daily_activity.get(day, 0) + 1

        # Calculate streaks
        current_streak, longest_streak = self._calculate_streaks(daily_activity)

        return {
            "daily_activity": daily_activity,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_active_days": len(daily_activity),
            "average_puzzles_per_day": len(recent_attempts) / 30
        }

    def _calculate_platform_engagement(self) -> Dict[str, Any]:
        """Calculate platform-wide engagement metrics"""
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)

        # Daily active users
        daily_active = self.db.query(
            func.date(PuzzleAttempt.created_at).label('date'),
            func.count(distinct(PuzzleAttempt.user_id)).label('users')
        ).filter(
            PuzzleAttempt.created_at >= thirty_days_ago
        ).group_by(
            func.date(PuzzleAttempt.created_at)
        ).all()

        # Puzzle completion rate
        total_attempts = self.db.query(PuzzleAttempt).filter(
            PuzzleAttempt.created_at >= thirty_days_ago
        ).count()

        successful_attempts = self.db.query(PuzzleAttempt).filter(
            PuzzleAttempt.created_at >= thirty_days_ago,
            PuzzleAttempt.is_correct == True
        ).count()

        return {
            "daily_active_users": {str(d.date): d.users for d in daily_active},
            "puzzle_completion_rate": (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0,
            "average_daily_active_users": sum(d.users for d in daily_active) / len(daily_active) if daily_active else 0
        }

    def _calculate_payment_stats(self) -> Dict[str, Any]:
        """Calculate payment-related statistics"""
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)

        # Get recent transactions
        transactions = self.db.query(Transaction).filter(
            Transaction.created_at >= thirty_days_ago,
            Transaction.status == TransactionStatus.COMPLETED
        ).all()

        daily_volume = {}
        for tx in transactions:
            day = tx.created_at.date()
            daily_volume[day] = daily_volume.get(day, 0) + tx.amount

        return {
            "total_volume": sum(tx.amount for tx in transactions),
            "average_transaction_size": sum(tx.amount for tx in transactions) / len(transactions) if transactions else 0,
            "daily_volume": daily_volume,
            "transaction_count": len(transactions)
        }
