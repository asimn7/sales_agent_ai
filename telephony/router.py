"""This code sets up a FastAPI APIRouter to handle HTTP requests related to 
telephony operations, specifically interacting with Twilio. It defines:

Webhook endpoints that Twilio calls at different stages of a phone call 
(e.g., when an incoming call arrives, when an outgoing call is answered). 
These endpoints typically respond with TwiML instructions.

A helper function to parse incoming data from Twilio requests.

An API endpoint that your application can call internally to trigger actions,
like initiating an outgoing call.
"""
from fastapi import APIRouter, Request, Depends, Response
from sqlalchemy.orm import Session
import phonenumbers # For cleaning phone numbers

from database.session import get_db
from database import crud
from services import greeting_service
from . import twilio_service # Import functions from the service module
from config import logger

router = APIRouter(
    prefix="/telephony", # Add prefix for organization
    tags=["Telephony"]   # Tag for Swagger UI
)

async def parse_twilio_request(request: Request) -> dict:
    """Helper to parse Twilio form data."""
    form_data = await request.form()
    call_sid = form_data.get('CallSid')
    from_number_raw = form_data.get('From')
    to_number_raw = form_data.get('To') # Needed for outgoing handler context

    # Clean and validate phone numbers (using phonenumbers library)
    from_number = None
    to_number = None
    try:
        if from_number_raw:
            parsed_from = phonenumbers.parse(from_number_raw, None) # Assume country if needed
            if phonenumbers.is_valid_number(parsed_from):
                from_number = phonenumbers.format_number(parsed_from, phonenumbers.PhoneNumberFormat.E164)
        if to_number_raw:
            parsed_to = phonenumbers.parse(to_number_raw, None)
            if phonenumbers.is_valid_number(parsed_to):
                to_number = phonenumbers.format_number(parsed_to, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException as e:
        logger.warning(f"Could not parse phone number: {e}")

    return {
        "call_sid": call_sid,
        "from_number": from_number,
        "to_number": to_number, # For outgoing call handler
        "speech_result": form_data.get('SpeechResult')
    }


@router.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming(request: Request, db: Session = Depends(get_db)):
    """Handles incoming calls to the main Twilio number."""
    try:
        data = await parse_twilio_request(request)
        call_sid = data["call_sid"]
        phone_number = data["from_number"]

        if not call_sid or not phone_number:
            logger.error("Missing CallSid or From number in Twilio request.")
            return Response(content="<Response><Say>Error processing call.</Say></Response>", media_type="application/xml")

        logger.info(f"Incoming call received - CallSid: {call_sid}, From: {phone_number}")

        # Get/Create Personal Info & Greeting
        full_name = crud.get_or_create_personal_info(db, phone_number, call_sid)
        logger.info(f"Caller Full Name (from DB): {full_name}")
        cleaned_number = phone_number.replace("+", "") # For filename/URL safety
        greeting_url_path = await greeting_service.get_greeting_url(full_name, cleaned_number)
        full_greeting_url = f"{request.base_url}{greeting_url_path.lstrip('/')}"

        # Generate TwiML to play greeting and connect to WebSocket
        twiml_content = twilio_service.create_greeting_and_connect_stream_twiml(
            full_greeting_url, call_sid, phone_number
        )
        return Response(content=twiml_content, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error handling incoming call: {e}", exc_info=True)
        return Response(content="<Response><Say>An internal error occurred.</Say></Response>", media_type="application/xml")


@router.api_route("/agent-incoming-call", methods=["GET", "POST"])
async def handle_agent_incoming(request: Request, db: Session = Depends(get_db)):
    """Handles incoming calls to numbers assigned to agents/carriers."""
    # Similar logic to handle_incoming, but might have different greeting logic
    # or context based on the 'To' number (the agent's assigned number)
    try:
        data = await parse_twilio_request(request)
        call_sid = data["call_sid"]
        phone_number = data["from_number"] # Caller's number
        agent_number = data["to_number"] # The number that was called

        if not call_sid or not phone_number or not agent_number:
            logger.error("Missing CallSid, From, or To number in Twilio agent request.")
            return Response(content="<Response><Say>Error processing call.</Say></Response>", media_type="application/xml")

        logger.info(f"Agent Incoming Call - CallSid: {call_sid}, From: {phone_number}, To: {agent_number}")

        # --- Add logic specific to agent calls ---
        # Maybe lookup carrier/agent based on agent_number?
        # Customize greeting?

        # Example: Use standard greeting for now
        full_name = crud.get_or_create_personal_info(db, phone_number, call_sid)
        cleaned_number = phone_number.replace("+", "")
        greeting_url_path = await greeting_service.get_greeting_url(full_name, cleaned_number)
        full_greeting_url = f"{request.base_url}{greeting_url_path.lstrip('/')}"

        twiml_content = twilio_service.create_greeting_and_connect_stream_twiml(
            full_greeting_url, call_sid, phone_number # Pass caller's number for context
        )
        return Response(content=twiml_content, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error handling agent incoming call: {e}", exc_info=True)
        return Response(content="<Response><Say>An internal error occurred.</Say></Response>", media_type="application/xml")


@router.api_route("/outgoing-call-handler", methods=["GET", "POST"])
async def handle_outgoing_handler(request: Request, db: Session = Depends(get_db)):
     """Provides TwiML when an outgoing call connects."""
     # This endpoint is requested by Twilio *after* twilio_service.make_twilio_outgoing_call
     # successfully initiates the call.
     try:
         data = await parse_twilio_request(request)
         call_sid = data["call_sid"]
         to_number = data["to_number"] # The number being called

         if not call_sid or not to_number:
             logger.error("Missing CallSid or To number in Twilio outgoing handler request.")
             return Response(content="<Response><Hangup/></Response>", media_type="application/xml")

         logger.info(f"Outgoing call connected - CallSid: {call_sid}, To: {to_number}")

         # Generate TwiML to say greeting and connect to WebSocket
         twiml_content = twilio_service.create_outgoing_connect_stream_twiml(
             call_sid, to_number # Pass context
         )
         return Response(content=twiml_content, media_type="application/xml")

     except Exception as e:
         logger.error(f"Error handling outgoing call handler: {e}", exc_info=True)
         return Response(content="<Response><Hangup/></Response>", media_type="application/xml")


# Example endpoint to trigger an outgoing call (can be used by a frontend/API)
@router.post("/initiate-call")
async def initiate_outgoing_call(to_number: str):
    """API endpoint to trigger making an outgoing call."""
    try:
        # Basic validation (can be improved)
        if not to_number or not to_number.startswith('+'):
             raise ValueError("Invalid 'to_number' format. Must be E.164.")

        call_sid = await twilio_service.make_twilio_outgoing_call(to_number)
        return {"status": "success", "message": "Outgoing call initiated.", "call_sid": call_sid}
    except Exception as e:
        logger.error(f"Failed to initiate outgoing call to {to_number}: {e}")
        # Return appropriate HTTP error
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")