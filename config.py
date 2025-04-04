import os
import logging
from dotenv import load_dotenv
from twilio.rest import Client
import openai
from pydantic_settings import BaseSettings # Use pydantic for settings management

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Manages application settings using Pydantic."""
    # Twilio Credentials
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str

    # OpenAI Credentials
    OPENAI_API_KEY: str

    # Application Settings
    PORT: int = 5050
    BASE_URL: str = f"http://localhost:{PORT}" # Default, might need adjustment for deployment
    DATABASE_URL: str = "sqlite:///./dispatch_agent.db" # Example DB URL

    # AI Settings
    OPENAI_REALTIME_MODEL: str = "gpt-4o-mini-realtime-preview-2024-12-17"
    OPENAI_EXTRACTION_MODEL: str = "gpt-4o-mini"
    AI_VOICE: str = "sage"
    LOG_EVENT_TYPES: List[str] = [
        'response.content.done', 'rate_limits.updated', 'response.done',
        'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
        'input_audio_buffer.speech_started', 'response.create', 'session.created'
    ]
    SHOW_TIMING_MATH: bool = False

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        # Allow extra fields if needed, though explicit declaration is better
        extra = 'ignore'


# Initialize settings instance
settings = Settings()

# Validate essential settings
if not settings.OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY environment variable.")
if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN or not settings.TWILIO_PHONE_NUMBER:
    raise ValueError("Missing Twilio credentials in environment variables.")

# Initialize OpenAI client
openai.api_key = settings.OPENAI_API_KEY

# Initialize Twilio client
twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

logger.info("Configuration loaded successfully.")
# You can now import 'settings', 'logger', 'twilio_client' from config