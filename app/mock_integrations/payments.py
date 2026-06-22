import logging
import uuid

logger = logging.getLogger(__name__)

class MockPaymentEscrow:
    """
    Mock integration for EasyPaisa / JazzCash payment gateways with Escrow functionality.
    """
    
    @staticmethod
    def initiate_escrow(booking_id: int, customer_id: int, amount: float) -> dict:
        """
        Simulate lock of funds in escrow.
        """
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        transaction_id = f"TXN-PAY-{uuid.uuid4().hex[:12].upper()}"
        logger.info(f"[PAYMENT ESCROW] Initiated escrow for booking {booking_id}. Customer {customer_id}, Amount {amount}. TxnID: {transaction_id}")
        return {
            "status": "success",
            "transaction_id": transaction_id,
            "escrow_status": "locked",
            "booking_id": booking_id,
            "amount": amount
        }

    @staticmethod
    def release_escrow(transaction_id: str) -> dict:
        """
        Simulate release of funds from escrow to provider.
        """
        if not transaction_id or not transaction_id.strip():
            raise ValueError("Transaction ID cannot be empty")
        logger.info(f"[PAYMENT ESCROW] Released escrow funds for transaction {transaction_id}")
        return {
            "status": "success",
            "transaction_id": transaction_id,
            "escrow_status": "released"
        }

    @staticmethod
    def refund_escrow(transaction_id: str) -> dict:
        """
        Simulate refunding escrow funds to customer.
        """
        if not transaction_id or not transaction_id.strip():
            raise ValueError("Transaction ID cannot be empty")
        logger.info(f"[PAYMENT ESCROW] Refunded escrow funds for transaction {transaction_id}")
        return {
            "status": "success",
            "transaction_id": transaction_id,
            "escrow_status": "refunded"
        }

