import httpx
from typing import Dict, Optional
from app.core.config import settings
from app.models.transaction import TransactionStatus, PaymentProvider

class MobileMoneyService:
    def __init__(self):
        self.mtn_base_url = "https://api.mtn.com/v1"  # Replace with actual MTN API URL
        self.airtel_base_url = "https://api.airtel.com/v1"  # Replace with actual Airtel API URL
        
        self.mtn_headers = {
            "Authorization": f"Bearer {settings.MTN_API_KEY}",
            "X-Reference-Id": "",
            "Content-Type": "application/json"
        }
        
        self.airtel_headers = {
            "Authorization": f"Bearer {settings.AIRTEL_API_KEY}",
            "Content-Type": "application/json"
        }

    async def initiate_payment(
        self,
        amount: float,
        phone_number: str,
        provider: PaymentProvider,
        reference: str
    ) -> Dict:
        """Initiate mobile money payment"""
        if provider == PaymentProvider.MTN:
            return await self._initiate_mtn_payment(amount, phone_number, reference)
        elif provider == PaymentProvider.AIRTEL:
            return await self._initiate_airtel_payment(amount, phone_number, reference)
        raise ValueError("Unsupported payment provider")

    async def _initiate_mtn_payment(self, amount: float, phone_number: str, reference: str) -> Dict:
        """Initiate MTN Mobile Money payment"""
        self.mtn_headers["X-Reference-Id"] = reference
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mtn_base_url}/collection",
                headers=self.mtn_headers,
                json={
                    "amount": str(amount),
                    "currency": "UGX",
                    "externalId": reference,
                    "payer": {
                        "partyIdType": "MSISDN",
                        "partyId": phone_number
                    },
                    "payerMessage": "FETU Optima Payment",
                    "payeeNote": "Prize Payment"
                }
            )
            
            if response.status_code != 202:
                raise ValueError(f"MTN payment failed: {response.text}")
                
            return {
                "provider_tx_id": response.headers.get("X-Reference-Id"),
                "status": TransactionStatus.PENDING
            }

    async def _initiate_airtel_payment(self, amount: float, phone_number: str, reference: str) -> Dict:
        """Initiate Airtel Money payment"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.airtel_base_url}/payments",
                headers=self.airtel_headers,
                json={
                    "reference": reference,
                    "subscriber": {
                        "country": "UG",
                        "currency": "UGX",
                        "msisdn": phone_number
                    },
                    "transaction": {
                        "amount": str(amount),
                        "country": "UG",
                        "currency": "UGX",
                        "id": reference
                    }
                }
            )
            
            if response.status_code != 200:
                raise ValueError(f"Airtel payment failed: {response.text}")
                
            data = response.json()
            return {
                "provider_tx_id": data["transaction"]["id"],
                "status": TransactionStatus.PENDING
            }

    async def check_payment_status(
        self,
        provider: PaymentProvider,
        provider_tx_id: str
    ) -> TransactionStatus:
        """Check payment status"""
        if provider == PaymentProvider.MTN:
            return await self._check_mtn_status(provider_tx_id)
        elif provider == PaymentProvider.AIRTEL:
            return await self._check_airtel_status(provider_tx_id)
        raise ValueError("Unsupported payment provider")

    async def _check_mtn_status(self, provider_tx_id: str) -> TransactionStatus:
        """Check MTN payment status"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.mtn_base_url}/collection/{provider_tx_id}",
                headers=self.mtn_headers
            )
            
            if response.status_code != 200:
                return TransactionStatus.FAILED
                
            data = response.json()
            status_map = {
                "SUCCESSFUL": TransactionStatus.COMPLETED,
                "FAILED": TransactionStatus.FAILED,
                "PENDING": TransactionStatus.PENDING,
                "CANCELLED": TransactionStatus.CANCELLED
            }
            return status_map.get(data["status"], TransactionStatus.FAILED)

    async def _check_airtel_status(self, provider_tx_id: str) -> TransactionStatus:
        """Check Airtel payment status"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.airtel_base_url}/payments/{provider_tx_id}",
                headers=self.airtel_headers
            )
            
            if response.status_code != 200:
                return TransactionStatus.FAILED
                
            data = response.json()
            status_map = {
                "TS": TransactionStatus.COMPLETED,  # Transaction Success
                "TF": TransactionStatus.FAILED,    # Transaction Failed
                "TP": TransactionStatus.PENDING,   # Transaction Pending
                "TC": TransactionStatus.CANCELLED  # Transaction Cancelled
            }
            return status_map.get(data["transaction"]["status"], TransactionStatus.FAILED)

    async def process_webhook(self, provider: PaymentProvider, payload: Dict) -> Optional[Dict]:
        """Process payment webhook"""
        if provider == PaymentProvider.MTN:
            return self._process_mtn_webhook(payload)
        elif provider == PaymentProvider.AIRTEL:
            return self._process_airtel_webhook(payload)
        raise ValueError("Unsupported payment provider")

    def _process_mtn_webhook(self, payload: Dict) -> Optional[Dict]:
        """Process MTN webhook"""
        return {
            "provider_tx_id": payload.get("referenceId"),
            "status": TransactionStatus.COMPLETED if payload.get("status") == "SUCCESSFUL" else TransactionStatus.FAILED,
            "amount": float(payload.get("amount", 0)),
            "currency": payload.get("currency"),
            "metadata": payload
        }

    def _process_airtel_webhook(self, payload: Dict) -> Optional[Dict]:
        """Process Airtel webhook"""
        transaction = payload.get("transaction", {})
        return {
            "provider_tx_id": transaction.get("id"),
            "status": TransactionStatus.COMPLETED if transaction.get("status") == "TS" else TransactionStatus.FAILED,
            "amount": float(transaction.get("amount", 0)),
            "currency": transaction.get("currency"),
            "metadata": payload
        }
