from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_async_db, ProviderModel, BookingModel, UserPushTokenModel
from app.tasks import expire_booking
from app.mock_integrations.payments import MockPaymentEscrow
from app.mock_integrations.sms import MockSMSGateway
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")

class ProviderCreate(BaseModel):
    name: str
    kyc_verified: bool
    category: str
    phone: str

class BookingCreate(BaseModel):
    customer_id: int
    amount: float
    customer_phone: str | None = None

class BookingAccept(BaseModel):
    provider_id: int

@router.post("/providers", status_code=status.HTTP_201_CREATED)
async def create_provider(provider: ProviderCreate, db: AsyncSession = Depends(get_async_db)):
    db_provider = ProviderModel(
        name=provider.name,
        kyc_verified=provider.kyc_verified,
        category=provider.category,
        phone=provider.phone
    )
    db.add(db_provider)
    await db.commit()
    return {"id": db_provider.id, "name": db_provider.name}

@router.post("/bookings", status_code=status.HTTP_201_CREATED)
async def create_booking(booking: BookingCreate, db: AsyncSession = Depends(get_async_db)):
    db_booking = BookingModel(
        customer_id=booking.customer_id,
        amount=booking.amount,
        status="pending",
        customer_phone=booking.customer_phone or "+923001234567"
    )
    db.add(db_booking)
    await db.commit()
    
    # Trigger Celery expiration task (in test mode, Celery task_always_eager will run this inline if triggered)
    # We trigger expire_booking on Celery queue
    expire_booking.apply_async(args=[db_booking.id], countdown=180)
    
    return {
        "id": db_booking.id,
        "customer_id": db_booking.customer_id,
        "status": db_booking.status,
        "amount": db_booking.amount
    }

@router.post("/bookings/{booking_id}/accept")
async def accept_booking(booking_id: int, accept_data: BookingAccept, db: AsyncSession = Depends(get_async_db)):
    query = select(BookingModel).where(BookingModel.id == booking_id)
    res = await db.execute(query)
    db_booking = res.scalar_one_or_none()
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    db_booking.status = "accepted"
    db_booking.provider_id = accept_data.provider_id
    await db.commit()
    return {"status": "success", "booking_id": booking_id, "booking_status": "accepted"}

@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: int, db: AsyncSession = Depends(get_async_db)):
    query = select(BookingModel).where(BookingModel.id == booking_id)
    res = await db.execute(query)
    db_booking = res.scalar_one_or_none()
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    old_status = db_booking.status
    db_booking.status = "canceled"
    
    # Refund escrow if transaction exists
    if db_booking.transaction_id:
        MockPaymentEscrow.refund_escrow(db_booking.transaction_id)
        # Fetch provider/customer phone
        phone = db_booking.customer_phone or "+923001234567"
        MockSMSGateway.send_sms(phone, f"Booking {booking_id} canceled. Refund processed.")
        
    await db.commit()
    return {"status": "success", "booking_id": booking_id, "booking_status": "canceled"}

@router.post("/bookings/{booking_id}/complete")
async def complete_booking(booking_id: int, db: AsyncSession = Depends(get_async_db)):
    query = select(BookingModel).where(BookingModel.id == booking_id)
    res = await db.execute(query)
    db_booking = res.scalar_one_or_none()
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    db_booking.status = "completed"
    
    # Release escrow if transaction exists
    if db_booking.transaction_id:
        MockPaymentEscrow.release_escrow(db_booking.transaction_id)
        # Send OTP code to verify payout
        provider_phone = "+923001234567"
        if db_booking.provider_id:
            res_p = await db.execute(select(ProviderModel).where(ProviderModel.id == db_booking.provider_id))
            provider = res_p.scalar_one_or_none()
            if provider and provider.phone:
                provider_phone = provider.phone
        MockSMSGateway.send_otp(provider_phone)
        
    await db.commit()
    return {"status": "success", "booking_id": booking_id, "booking_status": "completed"}

class PushTokenRegistration(BaseModel):
    user_id: int
    role: str
    push_token: str

@router.post("/push-token")
async def register_push_token(reg: PushTokenRegistration, db: AsyncSession = Depends(get_async_db)):
    if reg.role not in ["customer", "provider"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'customer' or 'provider'.")
    
    # Check if this token is already registered
    query = select(UserPushTokenModel).where(UserPushTokenModel.push_token == reg.push_token)
    res = await db.execute(query)
    existing_token = res.scalar_one_or_none()
    
    if existing_token:
        # Update user_id and role if changed
        existing_token.user_id = reg.user_id
        existing_token.role = reg.role
    else:
        # Check if there is already a token for this user/role, update it
        user_query = select(UserPushTokenModel).where(
            UserPushTokenModel.user_id == reg.user_id,
            UserPushTokenModel.role == reg.role
        )
        user_res = await db.execute(user_query)
        existing_user_token = user_res.scalar_one_or_none()
        
        if existing_user_token:
            existing_user_token.push_token = reg.push_token
        else:
            db_token = UserPushTokenModel(
                user_id=reg.user_id,
                role=reg.role,
                push_token=reg.push_token
            )
            db.add(db_token)
            
    await db.commit()
    return {"status": "success", "message": "Push token registered successfully"}
