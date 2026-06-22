from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")

@router.websocket("/ws/negotiation")
async def websocket_negotiation(
    websocket: WebSocket,
    token: str = Query(..., description="Mock JWT token containing user_id and role")
):
    """
    Establish bidding session.
    Subscribes to Redis Pub/Sub channel for the negotiation session (negotiation_{booking_id}).
    """
    # Accept connection
    await websocket.accept()
    
    # Placeholder login authentication and session routing (to be implemented in M3)
    try:
        while True:
            # Receive text or json
            data = await websocket.receive_json()
            # Message format: { "type": "bid"|"chat"|"accept", "booking_id": int, "sender_id": int, "role": "customer"|"provider", "amount": float, "message": str }
            logger.info(f"Received WS message: {data}")
            
            # Broadcast back/to Redis pub/sub backplane (to be implemented in M3)
            await websocket.send_json(data)
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
