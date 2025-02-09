from typing import Optional, Dict, Any
from pydantic import constr, confloat
from app.schemas.base import BaseSchema
from app.models.transaction import TransactionType, TransactionStatus, PaymentProvider

class TransactionBase(BaseSchema):
    """Base transaction schema"""
    type: TransactionType
    amount: confloat(gt=0)
    currency: constr(regex="^[A-Z]{3}$") = "UGX"
    provider: PaymentProvider
    phone_number: constr(regex="^[0-9]{10,12}$")
    description: Optional[str] = None

class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction"""
    metadata: Optional[Dict[str, Any]] = None

class TransactionUpdate(BaseSchema):
    """Schema for updating transaction details"""
    status: TransactionStatus
    provider_tx_id: Optional[str] = None
    error_message: Optional[str] = None

class TransactionInDB(TransactionBase):
    """Schema for transaction in database"""
    id: int
    user_id: int
    status: TransactionStatus
    provider_tx_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int

class TransactionOut(TransactionBase):
    """Schema for transaction response"""
    id: int
    status: TransactionStatus
    provider_tx_id: Optional[str]
    created_at: str

class PaymentInitiate(BaseSchema):
    """Schema for initiating a payment"""
    amount: confloat(gt=0)
    provider: PaymentProvider
    phone_number: constr(regex="^[0-9]{10,12}$")

class PaymentCallback(BaseSchema):
    """Schema for payment callback from provider"""
    provider_tx_id: str
    status: str
    amount: float
    currency: str
    metadata: Optional[Dict[str, Any]]

class WalletBalance(BaseSchema):
    """Schema for wallet balance"""
    balance: float
    currency: str = "UGX"
    pending_transactions: int
    total_earnings: float

class TransactionStats(BaseSchema):
    """Schema for transaction statistics"""
    total_transactions: int
    total_volume: float
    successful_transactions: int
    failed_transactions: int
    average_transaction_amount: float
