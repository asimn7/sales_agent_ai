import os # Standard library for interacting with the operating system (potentially useful, though pathlib is used more here)
from pathlib import Path # Modern library for object-oriented filesystem paths
from typing import Optional # Type hint for values that can be None
import openai # Import the official OpenAI client library for API calls

# Import necessary components from your project's configuration
# Assumes 'config.py' exists with 'settings' (holding API keys, AI voice choice, etc.) and a configured 'logger'
from config import settings, logger

# --- Constants and Setup ---
# Define the directory where generated audio files will be temporarily stored
# Using Path object for better path manipulation across different OS
TEMP_AUDIO_DIR = Path("temp_audio_path")
# Create the directory if it doesn't already exist.
# exist_ok=True prevents an error if the directory is already there.
TEMP_AUDIO_DIR.mkdir(exist_ok=True)

# --- Asynchronous Greeting Generation Function ---
async def get_greeting_url(full_name: Optional[str], phone_number_cleaned: str) -> str:
    """
    Generates a greeting audio file using OpenAI Text-to-Speech (TTS),
    saves it locally, and returns a relative URL path for serving the file.

    Args:
        full_name: The caller's full name, if known (used for personalization). None otherwise.
        phone_number_cleaned: The caller's phone number, cleaned of special characters
                              (e.g., '+', '-', ' ') suitable for use in filenames.

    Returns:
        A string representing the relative URL path to the generated audio file
        (e.g., "/temp_audio_path/greeting_1234567890.mp3").

    Raises:
        Exception: Can re-raise exceptions from the OpenAI API call or file saving
                   if error handling is not implemented with a fallback.
    """
    # --- Filename and Path Generation ---
    # Create a unique filename for the audio file using the cleaned phone number.
    # This helps in potentially reusing/caching greetings and avoids filename conflicts.
    # Using the *cleaned* number prevents issues with characters like '+' in filenames or URLs.
    greeting_filename = f"greeting_{phone_number_cleaned}.mp3"
    # Construct the full path to where the audio file will be saved.
    audio_file_path = TEMP_AUDIO_DIR / greeting_filename # pathlib uses '/' for joining paths

    # --- Greeting Text Generation ---
    # Determine the greeting text based on whether the caller's name is known.
    if full_name:
        # Personalized greeting for known callers
        greeting_text = f"Hi {full_name}, welcome back to Super Truck AI. How can I help you today?"
    else:
        # Generic greeting for unknown callers
        greeting_text = f"Hi there! I'm Alex, your sales agent at Super Truck AI. How can I assist you?"
        # Example of potentially adding more context (commented out)
        # greeting_text += " I can help with load dispatching, invoicing, accounting, IFTA filing, and optimizing your operations."

    # Log the generated greeting text for debugging/monitoring purposes
    logger.info(f"Generating greeting for {phone_number_cleaned}: '{greeting_text}'")

    # --- OpenAI TTS API Call and File Saving ---
    try:
        # Call the OpenAI TTS API asynchronously.
        # 'await' is used because this is an async function making a network request.
        # Ensure your openai client is initialized correctly (likely using settings.OPENAI_API_KEY)
        response = await openai.audio.speech.create(
            model="tts-1",          # Specify the TTS model (e.g., "tts-1", "tts-1-hd")
            voice=settings.AI_VOICE,# Use the AI voice specified in the application settings
            input=greeting_text,    # Provide the text to be converted to speech
        )

        # Save the audio content received from the API response to the local file.
        # The specific method (`stream_to_file`) depends on the OpenAI library version.
        # Always check the documentation for the current recommended way to save audio streams.
        # Using 'str(audio_file_path)' converts the Path object to a string, which might be required by the library function.
        response.stream_to_file(str(audio_file_path))

        # Log successful creation and saving of the audio file
        logger.info(f"Greeting audio saved to: {audio_file_path}")

    except Exception as e:
        # Catch any errors during the API call or file writing process.
        logger.error(f"Error generating greeting audio for {phone_number_cleaned}: {e}")
        # --- Fallback Strategy (Optional) ---
        # Option 1: Raise the exception to let the caller handle it.
        raise
        # Option 2: Return a path to a default, pre-recorded greeting file.
        # return f"/{TEMP_AUDIO_DIR.name}/default_greeting.mp3"
        # Option 3: Return None or an empty string and handle it downstream.
        # return None

    # --- Return Relative URL Path ---
    # Construct and return the relative URL path.
    # This path assumes that the 'TEMP_AUDIO_DIR.name' directory (e.g., 'temp_audio_path')
    # will be mounted and served as static files by the web framework (like FastAPI's StaticFiles).
    # Example: If TEMP_AUDIO_DIR is Path("temp_audio_path"), this returns "/temp_audio_path/greeting_1234567890.mp3"
    return f"/{TEMP_AUDIO_DIR.name}/{greeting_filename}"