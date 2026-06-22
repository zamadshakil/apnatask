import logging
import random

logger = logging.getLogger(__name__)

class MockSMSGateway:
    """
    Mock integration for SendPK / Jazz Direct OTP SMS gateways.
    """
    
    @staticmethod
    def send_otp(phone_number: str) -> str:
        """
        Generates and 'sends' a 6-digit OTP code to the provided phone number.
        Returns the generated OTP for validation/testing purposes.
        """
        otp = f"{random.randint(100000, 999999)}"
        logger.info(f"[SMS GATEWAY] OTP generated and sent to {phone_number}: {otp}")
        # Print to stdout so it can be seen in console logs during testing
        print(f"[SMS OTP] Phone: {phone_number} | Code: {otp}")
        return otp

    @staticmethod
    def send_sms(phone_number: str, message: str) -> bool:
        """
        Sends an arbitrary text message to the target phone number.
        """
        logger.info(f"[SMS GATEWAY] Sending SMS to {phone_number}: '{message}'")
        print(f"[SMS TEXT] To: {phone_number} | Msg: {message}")
        return True
