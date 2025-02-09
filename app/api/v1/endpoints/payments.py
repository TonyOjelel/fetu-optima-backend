from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.transaction import (
    TransactionCreate, TransactionOut, PaymentInitiate,
    PaymentCallback, WalletBalance, TransactionStats
)
from app.models.transaction import Transaction, TransactionStatus, PaymentProvider
from app.services.payment import MobileMoneyService
from app.websockets.server import send_puzzle_notification
import uuid

router = APIRouter()
payment_service = MobileMoneyService()

@router.post("/initiate", response_model=TransactionOut)
async def initiate_payment(
    payment: PaymentInitiate,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate a mobile money payment"""
    # Generate unique reference
    reference = str(uuid.uuid4())

    try:
        # Initiate payment with provider
        payment_result = await payment_service.initiate_payment(
            amount=payment.amount,
            phone_number=payment.phone_number,
            provider=payment.provider,
            reference=reference
        )

        # Create transaction record
        transaction = Transaction(
            user_id=current_user.id,
            type=TransactionType.DEPOSIT,
            status=payment_result["status"],
            amount=payment.amount,
            provider=payment.provider,
            provider_tx_id=payment_result["provider_tx_id"],
            phone_number=payment.phone_number
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        # Schedule background task to check payment status
        background_tasks.add_task(
            check_payment_status_task,
            transaction.id,
            payment_result["provider_tx_id"],
            payment.provider,
            db
        )

        return transaction

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook/{provider}")
async def payment_webhook(
    provider: PaymentProvider,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle payment provider webhooks"""
    payload = await request.json()
    
    # Verify webhook signature (implementation depends on provider)
    # verify_webhook_signature(request.headers, payload)
    
    try:
        # Process webhook
        webhook_data = await payment_service.process_webhook(provider, payload)
        if not webhook_data:
            return {"status": "ignored"}

        # Update transaction
        transaction = db.query(Transaction).filter(
            Transaction.provider_tx_id == webhook_data["provider_tx_id"]
        ).first()

        if not transaction:
            return {"status": "transaction_not_found"}

        transaction.status = webhook_data["status"]
        if transaction.status == TransactionStatus.COMPLETED:
            # Update user's wallet balance
            user = transaction.user
            user.wallet_balance += transaction.amount

        db.commit()

        # Send notification if transaction is completed
        if transaction.status == TransactionStatus.COMPLETED:
            background_tasks.add_task(
                send_puzzle_notification,
                transaction.user_id,
                None,
                "payment_success"
            )

        return {"status": "processed"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/wallet", response_model=WalletBalance)
async def get_wallet_balance(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's wallet balance"""
    pending_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.status == TransactionStatus.PENDING
    ).count()

    return {
        "balance": current_user.wallet_balance,
        "currency": "UGX",
        "pending_transactions": pending_transactions,
        "total_earnings": current_user.total_earnings
    }

@router.get("/transactions", response_model=list[TransactionOut])
async def get_transactions(
    skip: int = 0,
    limit: int = 10,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's transaction history"""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()
    return transactions

@router.get("/stats", response_model=TransactionStats)
async def get_transaction_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's transaction statistics"""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()

    successful_transactions = [t for t in transactions if t.status == TransactionStatus.COMPLETED]
    failed_transactions = [t for t in transactions if t.status == TransactionStatus.FAILED]

    return {
        "total_transactions": len(transactions),
        "total_volume": sum(t.amount for t in successful_transactions),
        "successful_transactions": len(successful_transactions),
        "failed_transactions": len(failed_transactions),
        "average_transaction_amount": sum(t.amount for t in successful_transactions) / len(successful_transactions) if successful_transactions else 0
    }

async def check_payment_status_task(
    transaction_id: int,
    provider_tx_id: str,
    provider: PaymentProvider,
    db: Session
):
    """Background task to check payment status"""
    MAX_RETRIES = 5
    RETRY_DELAY = 10  # seconds
    
    for _ in range(MAX_RETRIES):
        try:
            # Check payment status
            status = await payment_service.check_payment_status(provider, provider_tx_id)
            
            # Update transaction status
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if transaction and transaction.status != status:
                transaction.status = status
                if status == TransactionStatus.COMPLETED:
                    # Update user's wallet balance
                    user = transaction.user
                    user.wallet_balance += transaction.amount
                
                transaction.retry_count += 1
                db.commit()
                
                # Send notification if status is final
                if status in [TransactionStatus.COMPLETED, TransactionStatus.FAILED]:
                    await send_puzzle_notification(
                        transaction.user_id,
                        None,
                        f"payment_{status.lower()}"
                    )
                    break
            
            if status != TransactionStatus.PENDING:
                break
                
            await asyncio.sleep(RETRY_DELAY)
            
        except Exception as e:
            print(f"Error checking payment status: {e}")
            await asyncio.sleep(RETRY_DELAY)
