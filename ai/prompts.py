"""Overall Purpose:

The generate_openai_instructions function constructs the "system prompt" or 
initial instruction set that will be given to the OpenAI chat model at the beginning
of a conversation. Its key job is to provide the AI with:

Its core identity and purpose (acting as "Alex" from "Super Truck AI").
Context about the caller, specifically by summarizing past conversations if 
the caller (identified by phone_number) has interacted before.
This allows the AI to maintain continuity and provide a more personalized 
experience for returning callers"""

from sqlalchemy.orm import Session # Type hint for the database session object
from typing import List, Tuple, Optional # Standard type hints
from database import crud # Import the module containing database access functions (like get_past_conversations)
from config import settings # Import application settings (might be used indirectly by crud or for future enhancements)

# --- Base AI Instructions ---
# Defines the core persona, goals, and knowledge base for the AI agent "Alex".
# This is always included in the instructions.
BASE_INSTRUCTIONS = """
You are Alex, a friendly and professional sales agent for Super Truck AI,
a logistics software designed to help trucking carriers optimize their operations.
Your goal is to assist callers by understanding their needs, explaining how Super Truck AI
can benefit their business (load dispatching, invoicing, accounting, IFTA filing, carrier optimization),
and guiding them toward solutions—never push sales aggressively. Help carriers increase profits
and reduce costs by streamlining operations. Be concise and clear.
"""

# --- Additional Instructions for Returning Callers ---
# A short message added to the instructions if the system detects the caller has a history.
RETURNING_CALLER_INSTRUCTIONS = """
Remember you have spoken to this caller before. Refer to the previous conversation context below.
Continue the conversation naturally, acknowledging past discussions if relevant.
"""

# --- Instruction Generation Function ---
def generate_openai_instructions(db: Session, phone_number: Optional[str]) -> Tuple[str, bool]:
    """
    Generates the full instruction set (system prompt) for an OpenAI chat session.

    It starts with base instructions and adds context from past conversations
    retrieved from the database via the phone number, if available.

    Args:
        db: The active SQLAlchemy database session.
        phone_number: The caller's phone number (used to look up history). Can be None.

    Returns:
        A tuple containing:
        - full_instructions (str): The complete instruction string for the AI.
        - is_returning (bool): True if past conversations were found, False otherwise.
    """
    # Start with the default base instructions for "Alex".
    full_instructions = BASE_INSTRUCTIONS
    # Flag to indicate if the caller has previous conversations. Defaults to False.
    is_returning = False
    # String to build the summary of past conversations. Starts empty.
    dynamic_context = ""
    # Variable to potentially store the system message used in the last interaction (currently unused in final logic).
    previous_system_message = None

    # Only attempt to retrieve history if a phone number is provided.
    if phone_number:
        # Call the CRUD function to get past conversations for this number.
        # Assumes get_past_conversations returns a list of tuples, ordered newest first.
        past_conversations = crud.get_past_conversations(db, phone_number)

        # Check if any past conversations were returned.
        if past_conversations:
            # Mark the caller as returning.
            is_returning = True
            # Append the specific instruction note for returning callers.
            full_instructions += "\n" + RETURNING_CALLER_INSTRUCTIONS

            # --- Handling Previous System Message (Design Choice) ---
            # Check if the most recent conversation record has a stored system message.
            # past_conversations[0] is the latest; [1] accesses the system_message part of the tuple.
            if past_conversations[0][1]:
                previous_system_message = past_conversations[0][1]
                # **Decision Point:** How to use the previous system message?
                # Option 1: Replace base instructions entirely. Could be useful if the previous
                # message captured a very specific state, but might lose core persona info.
                # Example (commented out):
                # full_instructions = previous_system_message + "\n" + RETURNING_CALLER_INSTRUCTIONS
                #
                # Option 2 (Implicitly chosen here): Stick with BASE_INSTRUCTIONS + RETURNING note.
                # Add the conversation history as context (below). This is generally safer
                # as it ensures the core persona is always present.

            # --- Build Dynamic Context from Past Transcripts ---
            # Start the context section with a clear header.
            dynamic_context = "\n--- Previous Conversation Summary ---\n"
            # Iterate through the conversations in reverse order of retrieval (oldest first)
            # to present the history chronologically in the prompt.
            for i, (transcript, _) in enumerate(reversed(past_conversations)):
                 # Limit the length of each transcript summary to avoid overly long prompts
                 # (which increase cost and might exceed token limits). Appends '...' if truncated.
                 summary = transcript[:500] + '...' if len(transcript) > 500 else transcript
                 # Add the formatted summary for this past call.
                 dynamic_context += f"Call {len(past_conversations)-i}:\n{summary}\n\n" # Call numbers count up (1, 2, 3...)
            # Add a footer to clearly delimit the context section.
            dynamic_context += "--- End of Summary ---\n"

            # Append the generated dynamic context (summary of past calls) to the instructions.
            full_instructions += dynamic_context

    # Return the complete instruction string and the boolean flag.
    return full_instructions, is_returning