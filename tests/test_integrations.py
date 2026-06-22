import pytest
from app.mock_integrations.payments import MockPaymentEscrow
from app.mock_integrations.sms import MockSMSGateway

# Tier 1 Tests: Mock Integrations

def test_f4_t1_initiate_escrow_success():
    """Call payment escrow initiation, check transaction ID and 'locked' status."""
    res = MockPaymentEscrow.initiate_escrow(booking_id=1, customer_id=100, amount=500.0)
    assert res["status"] == "success"
    assert res["escrow_status"] == "locked"
    assert "transaction_id" in res
    assert res["booking_id"] == 1
    assert res["amount"] == 500.0

def test_f4_t1_release_escrow_success():
    """Call release escrow for locked transaction, check status becomes 'released'."""
    init_res = MockPaymentEscrow.initiate_escrow(booking_id=2, customer_id=101, amount=350.0)
    txn_id = init_res["transaction_id"]
    
    release_res = MockPaymentEscrow.release_escrow(txn_id)
    assert release_res["status"] == "success"
    assert release_res["escrow_status"] == "released"
    assert release_res["transaction_id"] == txn_id

def test_f4_t1_refund_escrow_success():
    """Call refund escrow for transaction, check status becomes 'refunded'."""
    init_res = MockPaymentEscrow.initiate_escrow(booking_id=3, customer_id=102, amount=120.0)
    txn_id = init_res["transaction_id"]
    
    refund_res = MockPaymentEscrow.refund_escrow(txn_id)
    assert refund_res["status"] == "success"
    assert refund_res["escrow_status"] == "refunded"
    assert refund_res["transaction_id"] == txn_id

def test_f4_t1_send_otp_code():
    """Send SMS OTP code, check that a 6-digit OTP code is returned."""
    otp = MockSMSGateway.send_otp("+923001234567")
    assert isinstance(otp, str)
    assert len(otp) == 6
    assert otp.isdigit()

def test_f4_t1_send_sms_success():
    """Send arbitrary SMS text, check that MockSMSGateway returns True."""
    res = MockSMSGateway.send_sms("+923001234567", "Hello from ApnaTask!")
    assert res is True


# Tier 2 Tests: Boundary & Corner Cases

def test_f4_t2_escrow_empty_txn_id():
    """Call release escrow with empty transaction ID, verify it raises ValueError."""
    with pytest.raises(ValueError, match="Transaction ID cannot be empty"):
        MockPaymentEscrow.release_escrow("")
        
    with pytest.raises(ValueError, match="Transaction ID cannot be empty"):
        MockPaymentEscrow.release_escrow("   ")

def test_f4_t2_escrow_refund_empty_txn_id():
    """Call refund escrow with empty transaction ID, verify error is raised."""
    with pytest.raises(ValueError, match="Transaction ID cannot be empty"):
        MockPaymentEscrow.refund_escrow("")
        
    with pytest.raises(ValueError, match="Transaction ID cannot be empty"):
        MockPaymentEscrow.refund_escrow("  ")

def test_f4_t2_sms_invalid_phone_format():
    """Try sending SMS to invalid phone number format, verify ValueError is raised."""
    # Too short
    with pytest.raises(ValueError, match="Invalid phone number format"):
        MockSMSGateway.send_sms("12345", "Short number")
        
    # Contains letters
    with pytest.raises(ValueError, match="Invalid phone number format"):
        MockSMSGateway.send_sms("+92300abc1234", "Letters in phone")

def test_f4_t2_escrow_negative_amount():
    """Try initiating escrow with amount <= 0, verify it is rejected."""
    # Zero amount
    with pytest.raises(ValueError, match="Amount must be greater than 0"):
        MockPaymentEscrow.initiate_escrow(1, 100, 0.0)
        
    # Negative amount
    with pytest.raises(ValueError, match="Amount must be greater than 0"):
        MockPaymentEscrow.initiate_escrow(1, 100, -50.0)

def test_f4_t2_send_otp_empty_phone():
    """Request OTP with empty phone number, verify it raises ValueError."""
    with pytest.raises(ValueError, match="Phone number cannot be empty"):
        MockSMSGateway.send_otp("")
        
    with pytest.raises(ValueError, match="Phone number cannot be empty"):
        MockSMSGateway.send_otp("   ")
