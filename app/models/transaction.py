from sqlalchemy import Column, String, Integer, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from app.models.base import BaseModel

class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    REWARD = "reward"
    REFUND = "refund"

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentProvider(str, enum.Enum):
    MTN = "mtn"
    AIRTEL = "airtel"

class Transaction(BaseModel):
    """Transaction model for handling payments"""
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # Transaction details
    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="UGX")
    
    # Payment details
    provider = Column(Enum(PaymentProvider), nullable=False)
    provider_tx_id = Column(String, unique=True, nullable=True)
    phone_number = Column(String, nullable=False)
    
    # Additional info
    description = Column(String)
    metadata = Column(JSON)
    
    # Error handling
    error_message = Column(String)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
