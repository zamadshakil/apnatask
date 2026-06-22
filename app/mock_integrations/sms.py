import logging
import random
import re

logger = logging.getLogger(__name__)

def validate_phone(phone_number: str):
    if not phone_number or not phone_number.strip():
        raise ValueError("Phone number cannot be empty")
    # Basic validation: check if phone consists of digits, optional leading plus, length between 10 and 15
    pattern = re.compile(r"^\+?[0-9]{10,15}$")
    if not pattern.match(phone_number):
        raise ValueError("Invalid phone number format")

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
        validate_phone(phone_number)
        otp = f"{random.randint(100000, 999999)}"
        logger.info(f"[SMS GATEWAY] OTP generated and sent to {phone_number}: {otp}")
        print(f"[SMS OTP] Phone: {phone_number} | Code: {otp}")
        return otp

    @staticmethod
    def send_sms(phone_number: str, message: str) -> bool:
        """
        Sends an arbitrary text message to the target phone number.
        """
        validate_phone(phone_number)
        logger.info(f"[SMS GATEWAY] Sending SMS to {phone_number}: '{message}'")
        print(f"[SMS TEXT] To: {phone_number} | Msg: {message}")
        return True

