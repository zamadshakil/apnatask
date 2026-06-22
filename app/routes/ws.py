from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
import logging
import json
import asyncio
from jose import jwt
import redis.asyncio as aioredis
from app.config import settings
from app.database import SessionLocal, BookingModel
from app.tasks import send_push_notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")

@router.get("/ws/negotiation")
async def websocket_negotiation_http_fallback(
    booking_id: int = Query(..., description="Booking ID for this negotiation session"),
    token: str = Query(..., description="Mock JWT token containing user_id and role")
):
    """
    HTTP fallback route to validate token/booking parameters.
    Used by clients or test suites checking handshake parameters.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        role = payload.get("role")
        if not user_id or role not in ["customer", "provider"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token claims")
    except Exception:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    return {"status": "valid"}

@router.websocket("/ws/negotiation")
async def websocket_negotiation(
    websocket: WebSocket,
    booking_id: int = Query(..., description="Booking ID for this negotiation session"),
    token: str = Query(..., description="Mock JWT token containing user_id and role")
):
    """
    Establish bidding session.
    Subscribes to Redis Pub/Sub channel for the negotiation session (negotiation_{booking_id}) immediately.
    """
    # 1. JWT Authentication
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        role = payload.get("role")
        if not user_id or role not in ["customer", "provider"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token claims")
    except Exception:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    await websocket.accept()
    
    redis_client = aioredis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"negotiation_{booking_id}")
    
    # Listener task to receive messages from Redis Pub/Sub and send them to the WebSocket
    async def redis_listener():
        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                if msg and msg["type"] == "message":
                    data = json.loads(msg["data"])
                    await websocket.send_json(data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in redis_listener: {e}")

    listener_task = asyncio.create_task(redis_listener())

    try:
        while True:
            try:
                raw_text = await websocket.receive_text()
            except WebSocketDisconnect:
                break
                
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Malformed JSON"})
                continue
                
            # Message field validation
            required_fields = ["type", "booking_id", "sender_id", "role"]
            if not all(field in data for field in required_fields):
                await websocket.send_json({"error": "Missing message fields"})
                continue
                
            msg_type = data["type"]
            msg_booking_id = data["booking_id"]
            sender_id = data["sender_id"]
            msg_role = data["role"]
            amount = data.get("amount", 0.0)
            
            # Validate sender role
            if msg_role not in ["customer", "provider"]:
                await websocket.send_json({"error": "Invalid role"})
                continue
                
            # Validate that message booking_id matches connection booking_id
            if msg_booking_id != booking_id:
                await websocket.send_json({"error": "Mismatch booking_id"})
                continue
                
            # Update booking provider and amount on bid from provider
            if msg_type == "bid" and msg_role == "provider":
                db = SessionLocal()
                try:
                    booking = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
                    if booking:
                        booking.provider_id = sender_id
                        booking.amount = amount
                        db.commit()
                        
                        # Trigger push notification
                        send_push_notification.delay(
                            booking.customer_id,
                            "customer",
                            f"New bid of Rs. {amount} placed by Provider #{sender_id}!"
                        )
                except Exception as e:
                    logger.error(f"Error updating booking on bid: {e}")
                finally:
                    db.close()

            # Trigger DB/Escrow flow on accept
            if msg_type == "accept":
                db = SessionLocal()
                try:
                    booking = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
                    if booking:
                        booking.status = "accepted"
                        booking.amount = amount
                        if msg_role == "provider":
                            booking.provider_id = sender_id
                        
                        # Initiate Escrow
                        from app.mock_integrations.payments import MockPaymentEscrow
                        res = MockPaymentEscrow.initiate_escrow(booking_id, booking.customer_id, amount)
                        booking.transaction_id = res["transaction_id"]
                        db.commit()
                        
                        data["transaction_id"] = res["transaction_id"]
                        data["escrow_status"] = "locked"
                except Exception as e:
                    logger.error(f"Error updating booking or initiating escrow: {e}")
                finally:
                    db.close()
                    
            # Publish message to Redis Pub/Sub channel
            await redis_client.publish(f"negotiation_{booking_id}", json.dumps(data))
            
    except Exception as e:
        logger.error(f"WebSocket session error: {e}")
    finally:
        listener_task.cancel()
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass

