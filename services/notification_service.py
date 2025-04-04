import asyncio
from typing import Optional

from config import logger

async def schedule_demo(
    transcript: str,
    call_sid: Optional[str],
    phone_number: Optional[str],
    # Add other relevant parameters like extracted name/email if available
    name: Optional[str] = None,
    email: Optional[str] = None
):
    """
    Handles the logic for scheduling a demo when requested.
    For now, it just logs the request. In a real scenario,
    this would integrate with a calendar API, CRM, or send an email notification.
    """
    log_message = f"Demo scheduling triggered for CallSid: {call_sid}, Phone: {phone_number}."
    if name: log_message += f" Name: {name}."
    if email: log_message += f" Email: {email}."
    log_message += f"\nRelevant Transcript Snippet: ...{transcript[-200:]}" # Log last part of transcript

    logger.info(log_message)

    # --- Placeholder for actual implementation ---
    # 1. Send an email notification to the sales team
    #    - Use libraries like smtplib, or services like SendGrid, Mailgun.
    #    - Example: await send_sales_notification(name, email, phone_number, transcript)
    # 2. Create an event in a calendar (Google Calendar API, Outlook Calendar API)
    #    - Example: await create_calendar_hold(name, email, phone_number)
    # 3. Create a task in a CRM (Salesforce API, HubSpot API)
    #    - Example: await create_crm_task(name, email, phone_number, "Demo Request")

    # Simulate async work if needed
    await asyncio.sleep(0.1)

    logger.info(f"Demo scheduling action placeholder completed for CallSid: {call_sid}.")

# Example helper function (conceptual)
# async def send_sales_notification(name, email, phone, transcript):
#     subject = f"Demo Request from {name or phone}"
#     body = f"""
#     A demo was requested during a call.
#     Caller Name: {name or 'N/A'}
#     Caller Email: {email or 'N/A'}
#     Caller Phone: {phone or 'N/A'}

#     Transcript context:
#     {transcript}
#     """
#     # ... code to send email ...
#     logger.info("Sales notification email sent.")