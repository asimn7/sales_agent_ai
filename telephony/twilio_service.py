"""This code provides utility functions to:

Generate TwiML (Twilio Markup Language) strings. 
TwiML instructs Twilio on how to handle a phone call (e.g., play audio, say text, connect to a stream).
Initiate outgoing phone calls using the Twilio REST API.
Search for and purchase Twilio phone numbers using the REST API. 
These functions bridge the application's logic with Twilio's capabilities,
setting up calls to be connected to the real-time AI handler via Media Streams."""

import asyncio # Used for asyncio.to_thread to run sync code in async apps
from twilio.twiml.voice_response import VoiceResponse, Connect # Twilio helper library classes for generating TwiML
from config import twilio_client, settings, logger # Import configured Twilio client, app settings, and logger
from typing import Optional # Type hint for optional return values

# --- TwiML Generation Functions ---

def create_greeting_and_connect_stream_twiml(
    greeting_audio_url: Optional[str], # URL of a pre-generated audio file to play (can be None)
    call_sid: str,                     # The specific Call SID for context
    phone_number: str                  # The caller's phone number for context
    ) -> str:
    """
    Generates TwiML for an INCOMING call. It plays a greeting audio (if provided)
    or says a fallback message, then connects the call's audio
    to the media stream WebSocket endpoint.

    Args:
        greeting_audio_url: The publicly accessible URL of the greeting MP3/WAV file. None if greeting failed.
        call_sid: The Twilio Call SID of the current call.
        phone_number: The phone number of the caller.

    Returns:
        A string containing the generated TwiML XML.
    """
    # Instantiate a TwiML VoiceResponse object
    response = VoiceResponse()

    # Check if a greeting audio URL was successfully generated/provided
    if greeting_audio_url:
        # If yes, instruct Twilio to play the audio file from the URL
        response.play(greeting_audio_url)
        # Optional: Add a short pause after the greeting
        response.pause(length=1)
    else:
        # If no greeting URL (e.g., TTS failed), play a generic fallback message
        response.say("Connecting your call.") # Use Twilio's default TTS

    # Create a TwiML <Connect> verb object
    connect = Connect()

    # Define the WebSocket URL for the media stream.
    # It points to the endpoint handled by `media_stream_endpoint`.
    # Crucially, it embeds the call_sid and phone_number in the URL path
    # so the WebSocket handler knows the context of the connection.
    # Assumes settings.BASE_URL is like 'http://yourdomain.com' or 'https://yourdomain.com'
    # .split('//')[1] extracts 'yourdomain.com'
    websocket_url = f"wss://{settings.BASE_URL.split('//')[1]}/media-stream/{call_sid}/{phone_number}"
    logger.info(f"[{call_sid}] Generating TwiML to connect INCOMING call to WebSocket: {websocket_url}")

    # Instruct Twilio to stream the call's audio using the <Stream> noun within <Connect>.
    # Twilio will initiate a WebSocket connection to this URL.
    connect.stream(url=websocket_url)

    # Append the <Connect> verb (containing the <Stream>) to the main response
    response.append(connect)

    # Return the entire TwiML response as an XML string
    return str(response)


def create_outgoing_connect_stream_twiml(
    call_sid: str,      # The specific Call SID for context
    to_phone_number: str # The number being called for context
) -> str:
    """
    Generates TwiML for an OUTGOING call *after* it has been answered.
    It says a brief initial greeting (as the AI) and then immediately
    connects the call's audio to the media stream WebSocket endpoint.

    Args:
        call_sid: The Twilio Call SID of the outgoing call.
        to_phone_number: The phone number that was dialed.

    Returns:
        A string containing the generated TwiML XML.
    """
    # Instantiate a TwiML VoiceResponse object
    response = VoiceResponse()

    # Instruct Twilio to say an initial greeting using its TTS.
    # This is heard by the person who answers the outgoing call.
    response.say("Hello! This is Alex from Super Truck AI.")

    # Create a TwiML <Connect> verb object
    connect = Connect()

    # Define the WebSocket URL, embedding context for the outgoing call.
    websocket_url = f"wss://{settings.BASE_URL.split('//')[1]}/media-stream/{call_sid}/{to_phone_number}"
    logger.info(f"[{call_sid}] Generating TwiML to connect OUTGOING call to WebSocket: {websocket_url}")

    # Instruct Twilio to stream the call's audio to our WebSocket endpoint.
    connect.stream(url=websocket_url)

    # Append the <Connect> verb to the response
    response.append(connect)

    # Return the TwiML response as an XML string
    return str(response)


# --- Twilio REST API Interaction Functions ---

async def make_twilio_outgoing_call(to_phone_number: str) -> str:
    """
    Initiates an outgoing phone call using the Twilio REST API client.

    Args:
        to_phone_number: The destination phone number to call.

    Returns:
        The CallSid (string) of the initiated call.

    Raises:
        Exception: Re-raises exceptions from the Twilio API call.
    """
    try:
        logger.info(f"Initiating outgoing call to {to_phone_number} from {settings.TWILIO_PHONE_NUMBER}")
        # The Twilio Python helper library's methods (like calls.create) are synchronous.
        # In an async application (like FastAPI), blocking calls should be run
        # in a separate thread to avoid blocking the main event loop.
        # `asyncio.to_thread` is the standard way to achieve this.
        call = await asyncio.to_thread(
            twilio_client.calls.create, # The synchronous function to run
            to=to_phone_number,         # Destination number
            from_=settings.TWILIO_PHONE_NUMBER, # Your Twilio number from settings
            # The 'url' parameter is a webhook URL. Twilio will make an HTTP request
            # to this URL *when the called party answers*. This URL should point to
            # an endpoint in *this* application that returns the TwiML generated by
            # `create_outgoing_connect_stream_twiml`.
            url=f"{settings.BASE_URL}/telephony/outgoing-call-handler" # Example webhook URL
        )
        logger.info(f"Outgoing call initiated successfully to {to_phone_number}, CallSid: {call.sid}")
        # Return the unique identifier for the newly created call
        return call.sid
    except Exception as e:
        logger.error(f"Error making Twilio outgoing call to {to_phone_number}: {e}")
        # Re-raise the exception to be handled by the calling function/route
        raise


async def buy_twilio_number(area_code: int) -> Optional[str]:
      """
      Searches for an available US local phone number in a given area code
      using the Twilio REST API and attempts to purchase the first one found.

      Args:
          area_code: The US area code (e.g., 510) to search within.

      Returns:
          The purchased phone number (string) in E.164 format (e.g., +15105551234),
          or None if no number is available or an error occurs.
      """
      try:
            logger.info(f"Searching for available Twilio numbers in area code {area_code}")
            # Use asyncio.to_thread again for the synchronous Twilio SDK call
            available_numbers = await asyncio.to_thread(
                twilio_client.available_phone_numbers("US").local.list, # Sync function
                area_code=area_code, # Filter by area code
                limit=1              # Only need to find one number
            )

            # Check if the search returned any numbers
            if available_numbers:
                # Get the phone number string from the first result
                number_to_buy_struct = available_numbers[0]
                number_to_buy = number_to_buy_struct.phone_number
                logger.info(f"Found available number: {number_to_buy}. Attempting to purchase...")

                # Attempt to purchase the found number using another sync SDK call
                purchased_number = await asyncio.to_thread(
                    twilio_client.incoming_phone_numbers.create, # Sync function
                    phone_number=number_to_buy # Specify the number to purchase
                )
                logger.info(f"Successfully purchased number: {purchased_number.phone_number} (SID: {purchased_number.sid})")
                # Return the phone number string of the purchased number
                return purchased_number.phone_number
            else:
                # Log a warning if no numbers were found for the area code
                logger.warning(f"No available Twilio numbers found for area code {area_code}")
                return None # Return None indicating no number was purchased
      except Exception as e:
            # Log any errors during the search or purchase process
            logger.error(f"Error searching/buying Twilio number for area code {area_code}: {e}")
            return None # Return None indicating failure