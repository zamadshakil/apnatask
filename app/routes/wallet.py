"""
Wallet & Bidding API routes for ApnaTask service providers.

Endpoints:
  GET  /api/v1/provider/{provider_id}/wallet       — Get wallet balance
  POST /api/v1/provider/{provider_id}/wallet/topup  — Add money to wallet
  POST /api/v1/bookings/{booking_id}/bid            — Place a bid (deducts commission)
  GET  /api/v1/bookings/{booking_id}/bids           — List bids for a booking
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_async_db, WalletModel, BidModel, BookingModel, ProviderModel
from app.tasks import send_push_notification
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")

# Minimum wallet balance required to place a bid (PKR)
MIN_BID_BALANCE = 100.0
# Platform commission per bid (PKR) — deducted from wallet
BID_COMMISSION = 25.0


# --- Schemas ---

class WalletResponse(BaseModel):
    provider_id: int
    balance: float

class TopupRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to add in PKR")

class BidRequest(BaseModel):
    provider_id: int
    amount: float = Field(..., gt=0, description="Bid amount in PKR")

class BidResponse(BaseModel):
    id: int
    booking_id: int
    provider_id: int
    amount: float
    status: str
    provider_name: str | None = None
    kyc_verified: bool = False


# --- Wallet Endpoints ---

@router.get("/provider/{provider_id}/wallet", response_model=WalletResponse)
async def get_wallet(provider_id: int, db: AsyncSession = Depends(get_async_db)):
    """Get wallet balance for a provider. Creates wallet if it doesn't exist."""
    result = await db.execute(
        select(WalletModel).where(WalletModel.provider_id == provider_id)
    )
    wallet = result.scalar_one_or_none()

    if not wallet:
        # Auto-create wallet for new providers
        wallet = WalletModel(provider_id=provider_id, balance=0.0)
        db.add(wallet)
        await db.commit()

    return WalletResponse(provider_id=provider_id, balance=wallet.balance)


@router.post("/provider/{provider_id}/wallet/topup", response_model=WalletResponse)
async def topup_wallet(
    provider_id: int,
    topup: TopupRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Add money to provider wallet.
    In production, this would integrate with EasyPaisa/JazzCash payment gateways.
    """
    result = await db.execute(
        select(WalletModel).where(WalletModel.provider_id == provider_id)
    )
    wallet = result.scalar_one_or_none()

    if not wallet:
        wallet = WalletModel(provider_id=provider_id, balance=0.0)
        db.add(wallet)
        await db.flush()

    wallet.balance += topup.amount
    await db.commit()

    logger.info(f"Provider {provider_id} topped up {topup.amount} PKR. New balance: {wallet.balance}")
    return WalletResponse(provider_id=provider_id, balance=wallet.balance)


# --- Bidding Endpoints ---

@router.post("/bookings/{booking_id}/bid", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def place_bid(
    booking_id: int,
    bid_req: BidRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Place a bid on a booking. Requires minimum wallet balance.
    Deducts a platform commission from the provider's wallet.
    """
    # 1. Verify booking exists and is still open
    booking_result = await db.execute(
        select(BookingModel).where(BookingModel.id == booking_id)
    )
    booking = booking_result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status not in ("pending", "bidding"):
        raise HTTPException(status_code=400, detail="Booking is no longer accepting bids")

    # 2. Check wallet balance
    wallet_result = await db.execute(
        select(WalletModel).where(WalletModel.provider_id == bid_req.provider_id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet or wallet.balance < MIN_BID_BALANCE:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient wallet balance. Minimum {MIN_BID_BALANCE} PKR required to bid."
        )

    # 3. Deduct commission
    wallet.balance -= BID_COMMISSION

    # 4. Create bid record
    new_bid = BidModel(
        booking_id=booking_id,
        provider_id=bid_req.provider_id,
        amount=bid_req.amount,
        status="pending",
    )
    db.add(new_bid)

    # 5. Update booking status to 'bidding' if it was 'pending'
    if booking.status == "pending":
        booking.status = "bidding"

    await db.commit()

    # Fetch provider name for response
    provider_result = await db.execute(
        select(ProviderModel).where(ProviderModel.id == bid_req.provider_id)
    )
    provider = provider_result.scalar_one_or_none()

    # Trigger push notification to the customer
    provider_name = provider.name if provider else "A provider"
    send_push_notification.delay(
        booking.customer_id,
        "customer",
        f"New bid of Rs. {bid_req.amount} placed by {provider_name}!"
    )

    logger.info(f"Provider {bid_req.provider_id} bid {bid_req.amount} PKR on booking {booking_id}")

    return BidResponse(
        id=new_bid.id,
        booking_id=booking_id,
        provider_id=bid_req.provider_id,
        amount=bid_req.amount,
        status="pending",
        provider_name=provider.name if provider else None,
        kyc_verified=provider.kyc_verified if provider else False,
    )


@router.get("/bookings/{booking_id}/bids", response_model=list[BidResponse])
async def list_bids(booking_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    List all bids for a booking.
    Customers use this to see who bid and at what price.
    """
    result = await db.execute(
        select(BidModel).where(BidModel.booking_id == booking_id)
    )
    bids = result.scalars().all()

    response = []
    for bid in bids:
        # Fetch provider info
        p_result = await db.execute(
            select(ProviderModel).where(ProviderModel.id == bid.provider_id)
        )
        provider = p_result.scalar_one_or_none()

        response.append(BidResponse(
            id=bid.id,
            booking_id=bid.booking_id,
            provider_id=bid.provider_id,
            amount=bid.amount,
            status=bid.status,
            provider_name=provider.name if provider else None,
            kyc_verified=provider.kyc_verified if provider else False,
        ))

    return response
