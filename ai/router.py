"""This code defines a specific WebSocket endpoint within a FastAPI application. 
This endpoint (/media-stream/{call_sid}/{phone_number}) is designed
to be the target URL that Twilio connects to when you initiate a Media Stream
for a phone call. Once connected, it instantiates the RealtimeOpenAIHandler
(which we analyzed previously) to manage the real-time audio processing
and AI interaction for that specific call. It handles the lifecycle
of the WebSocket connection and ensures the handler is properly started and stopped."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path as FastApiPath
from sqlalchemy.orm import Session
from fastapi import Depends

from database.session import SessionLocal # Import factory, not get_db for WebSocket
from ai.openai_services import RealtimeOpenAIHandler
from config import logger

router = APIRouter()

@router.websocket("/media-stream/{call_sid}/{phone_number}")
async def media_stream_endpoint(
    websocket: WebSocket,
    call_sid: str = FastApiPath(...),
    phone_number: str = FastApiPath(...) # Get context from URL path
):
    """Handles the WebSocket connection for Twilio media streams."""
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for CallSid: {call_sid}, Phone: {phone_number}")

    # Use the session factory directly for the handler instance
    handler = RealtimeOpenAIHandler(websocket, SessionLocal, call_sid, phone_number)

    try:
        await handler.start()
    except WebSocketDisconnect:
        logger.info(f"[{call_sid}] Twilio WebSocket disconnected.")
        await handler.stop() # Ensure handler cleans up
    except Exception as e:
        logger.error(f"[{call_sid}] Error in WebSocket endpoint: {e}")
        await handler.stop() # Ensure handler cleans up
    finally:
        logger.info(f"[{call_sid}] WebSocket connection handler finished.")
        # Ensure handler is stopped if not already
        await handler.stop()