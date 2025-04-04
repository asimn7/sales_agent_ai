"""Overall Purpose:

This script serves as the main entry point for your "SuperTruck AI Voice Agent" 
web application. It does the following:

Initializes necessary components (like the database).
Creates the central FastAPI application instance.
Configures the application by mounting directories for static files 
(like CSS, JS, or generated audio) and including API routers defined in other modules.
Defines a simple root endpoint (/).
Uses the Uvicorn ASGI server to run the FastAPI application, 
making it accessible via HTTP/WebSocket."""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# Import configurations and routers
from config import settings, logger
from database.session import init_db # Import DB initializer
from telephony.router import router as telephony_router
from ai.router import router as ai_router
from assistants.router import router as assistants_router # Assuming this exists

# Initialize the database (create tables etc.)
init_db()

# Create FastAPI app instance
app = FastAPI(title="SuperTruck AI Voice Agent")

# Mount static file directories
# Ensure these directories exist
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/temp_audio_path", StaticFiles(directory="temp_audio_path"), name="temp_audio_path")

# Include routers from different modules
app.include_router(telephony_router)
app.include_router(ai_router)
app.include_router(assistants_router) # Include the assistants router

# Root endpoint for health check / basic info
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return "<html><body><h1>SuperTruck AI Voice Agent is running!</h1></body></html>"

# --- Add any global middleware or exception handlers here if needed ---

# Main execution block
if __name__ == "__main__":
    logger.info(f"Starting SuperTruck AI Voice Agent on port {settings.PORT}")
    uvicorn.run(
        "main:app", # Point to the FastAPI app instance
        host="0.0.0.0",
        port=settings.PORT,
        reload=True # Enable auto-reload for development (disable in production)
        # Add SSL configuration here if needed for production WSS
        # ssl_keyfile="path/to/key.pem",
        # ssl_certfile="path/to/cert.pem"
    )