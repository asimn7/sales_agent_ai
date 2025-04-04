""""Overall Purpose:

The extract_name_and_email_from_text asynchronous function
takes a string of text (likely a transcript or message) and uses
an OpenAI language model (specifically via the Chat Completions endpoint) 
to identify and extract any full name and email address mentioned within
that text. It's designed to return the results in a structured way (a tuple)
and handle cases
where the information isn't found or an error occurs."""

import openai # Import the official OpenAI client library
from typing import Tuple, Optional # Import type hints for clarity and static analysis
from config import settings, logger # Import application settings (API keys, model names) and logger

async def extract_name_and_email_from_text(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Uses an OpenAI Chat Completion model to extract a person's full name and
    email address from a given block of text.

    Args:
        text: The input string (e.g., conversation transcript) to analyze.

    Returns:
        A tuple containing:
        (extracted_name: Optional[str], extracted_email: Optional[str])
        Each element will be the extracted string or None if not found or an error occurred.
    """
    # --- Input Validation ---
    # Check if the input text is empty or contains only whitespace.
    # If so, extraction is impossible, return None for both fields immediately.
    if not text or not text.strip():
        logger.debug("Input text for name/email extraction is empty.")
        return None, None

    # --- Prompt Engineering ---
    # Define the prompt that instructs the AI model on what to do.
    # This prompt specifies the task, how to handle missing information ('None'),
    # and crucially, the exact output format required for reliable parsing later.
    prompt = f"""
    Analyze the following text and extract the person's full name and email address if present.
    If a name is mentioned, provide the full name.
    If an email address is mentioned, provide the email address.
    If either is not found, output 'None' for that field.
    Format the output *exactly* as: Name: [extracted name or None] | Email: [extracted email or None]

    Text: "{text}"
    """

    # --- OpenAI API Call ---
    try:
        # Log the attempt to extract information.
        logger.debug(f"Attempting to extract name/email from text: '{text[:100]}...'")

        # Make an asynchronous call to the OpenAI Chat Completions endpoint.
        # 'await' is used because this function and the API call are asynchronous.
        response = await openai.chat.completions.create(
            # Specify the model to use, configured in application settings.
            # Different models may have varying performance and cost for extraction tasks.
            model=settings.OPENAI_EXTRACTION_MODEL,
            messages=[
                # System message sets the context/role for the AI. It reinforces the output format.
                {"role": "system", "content": "You are an expert text analysis assistant. Extract names and emails precisely. Output only in the format 'Name: [name/None] | Email: [email/None]'."},
                # User message provides the specific instructions and the text to analyze.
                {"role": "user", "content": prompt}
            ],
            # Low temperature makes the output more deterministic and focused, suitable for extraction.
            temperature=0.1,
            # Limit the maximum number of tokens in the response to control cost and prevent overly long/irrelevant answers.
            # 50 tokens should be sufficient for the "Name: ... | Email: ..." format.
            max_tokens=50
        )
        # Extract the text content from the first choice in the response.
        result_text = response.choices[0].message.content.strip()
        # Log the raw response from the AI for debugging.
        logger.debug(f"Name/Email extraction raw result: '{result_text}'")

        # --- Response Parsing ---
        # Initialize variables to store extracted data. Default to None.
        extracted_name = None
        extracted_email = None

        # Parse the structured output based on the format requested in the prompt.
        parts = result_text.split('|') # Split the response by the expected separator '|'
        if len(parts) == 2: # Expecting two parts: Name and Email
            # Parse the Name part
            name_part = parts[0].split('Name:', 1) # Split by 'Name:' separator (limit to 1 split)
            if len(name_part) == 2:
                name_str = name_part[1].strip() # Get the value after 'Name:' and remove whitespace
                # Check if the extracted value is not the literal string 'None' (case-insensitive)
                if name_str.lower() != 'none':
                    extracted_name = name_str # Assign the found name

            # Parse the Email part
            email_part = parts[1].split('Email:', 1) # Split by 'Email:' separator
            if len(email_part) == 2:
                email_str = email_part[1].strip() # Get the value after 'Email:'
                # Check if the extracted value is not 'None'
                if email_str.lower() != 'none':
                    # Perform a very basic check to see if it looks like an email.
                    # This could be replaced with more robust regex validation if needed.
                    if '@' in email_str and '.' in email_str:
                        extracted_email = email_str # Assign the found email

        # Log the final parsed results.
        logger.info(f"Parsed extraction results - Name: {extracted_name}, Email: {extracted_email}")
        # Return the parsed (or None) name and email.
        return extracted_name, extracted_email

    # --- Error Handling ---
    except Exception as e:
        # Log any exception that occurs during the API call or parsing.
        logger.error(f"Error extracting name/email from text '{text[:50]}...': {e}")
        # Return None for both fields in case of any error.
        return None, None