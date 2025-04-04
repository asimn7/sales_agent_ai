# Import the Session type hint from SQLAlchemy ORM
from sqlalchemy.orm import Session
# Import standard Python type hints for clarity
from typing import List, Tuple, Optional

# Import your specific SQLAlchemy model classes defined elsewhere (e.g., in models.py)
from .models import PersonalInfoDB, CarrierDB, AssistantDB, ConversationDB

# --- PersonalInfoDB Functions ---


def get_or_create_personal_info(db: Session, phone_number: str, call_sid: Optional[str] = None) -> Optional[str]:
    """
    Retrieves a PersonalInfoDB record by phone number.
    If it exists, returns the full_name and potentially updates the call_sid.
    If it doesn't exist, creates a new record with the phone number and call_sid,
    commits it, and returns None (since full_name is not yet known).

    Args:
        db: The active SQLAlchemy session.
        phone_number: The phone number to search for or create.
        call_sid: The call identifier (optional), potentially from Twilio.

    Returns:
        The full_name string if the record existed, otherwise None.
    """
    # Query the PersonalInfoDB table
    record = db.query(PersonalInfoDB).filter(
        PersonalInfoDB.phone_number == phone_number).first()

    # If a record with this phone number already exists
    if record:
        # Optional: Update the call_sid if a new one is provided and differs from the stored one
        if call_sid and record.call_sid != call_sid:
            record.call_sid = call_sid
            db.commit()  # Commit the change to call_sid
        # Return the existing full name (which might be None if never updated)
        return record.full_name
    # If no record exists for this phone number
    else:
        # Create a new PersonalInfoDB object instance
        new_record = PersonalInfoDB(
            phone_number=phone_number, call_sid=call_sid)
        # Add the new object to the session (stages it for insertion)
        db.add(new_record)
        # Commit the transaction to save the new record to the database
        db.commit()
        # Optional: Refresh the instance to load any db-generated values (like ID) if needed later
        # db.refresh(new_record)
        # Return None because we just created the record and don't have a full_name yet
        return None


def update_personal_info(db: Session, phone_number: str, name: Optional[str], email: Optional[str]) -> bool:
    """
    Updates the full_name and/or email for an existing PersonalInfoDB record
    identified by the phone number.

    Args:
        db: The active SQLAlchemy session.
        phone_number: The phone number of the record to update.
        name: The new full name (if provided).
        email: The new email address (if provided).

    Returns:
        True if the record was found and updated, False otherwise.
    """
    # Find the record by phone number
    record = db.query(PersonalInfoDB).filter(
        PersonalInfoDB.phone_number == phone_number).first()

    # If the record exists
    if record:
        updated = False  # Flag to track if any changes were made
        # If a new name is provided and it's different from the current one
        if name and record.full_name != name:
            record.full_name = name
            updated = True
        # If a new email is provided and it's different from the current one
        if email and record.email != email:
            record.email = email
            updated = True
        # If any field was actually updated
        if updated:
            db.commit()  # Commit the transaction to save changes
            return True  # Indicate success
    # If the record was not found or no changes were needed
    return False

# --- ConversationDB Functions ---


def get_past_conversations(db: Session, phone_number: str, limit: int = 3) -> List[Tuple[str, Optional[str]]]:
    """
    Retrieves a specified number of the most recent conversation records
    for a given phone number, ordered by descending ID (newest first).

    Args:
        db: The active SQLAlchemy session.
        phone_number: The phone number whose conversations are to be retrieved.
        limit: The maximum number of conversations to return.

    Returns:
        A list of tuples, where each tuple contains (transcript, system_message).
    """
    # Query the ConversationDB table
    conversations = (db.query(ConversationDB)
                     .filter(ConversationDB.phone_number == phone_number)
                     .order_by(ConversationDB.id.desc())
                     .limit(limit)
                     .all())

    # Return a list comprehension extracting the desired fields into tuples
    return [(conv.transcript, conv.system_message) for conv in conversations]


def save_conversation(db: Session, phone_number: str, transcript: str, system_message: str):
    """
    Creates and saves a new conversation record to the database.

    Args:
        db: The active SQLAlchemy session.
        phone_number: The phone number associated with the conversation.
        transcript: The text transcript of the conversation.
        system_message: Any associated system message or context.
    """
    # Create a new ConversationDB object instance
    conversation = ConversationDB(
        phone_number=phone_number,
        transcript=transcript,
        system_message=system_message
        # Assumes the 'timestamp' field in the model has a default value (e.g., default=func.now())
    )
    # Add the new object to the session
    db.add(conversation)
    # Commit the transaction to save the record
    db.commit()
    # Optional: Refresh if you need the newly generated ID immediately
    # db.refresh(conversation)

# --- CarrierDB and AssistantDB Functions ---


def find_carrier_by_phone(db: Session, phone_number: str) -> Optional[CarrierDB]:
    """
    Finds a single carrier record based on their phone number.

    Args:
        db: The active SQLAlchemy session.
        phone_number: The carrier's phone number to search for.

    Returns:
        The CarrierDB object if found, otherwise None.
    """
    # Query CarrierDB, filter by phone, get the first result or None
    return db.query(CarrierDB).filter(CarrierDB.phone == phone_number).first()


def find_assistant_by_carrier(db: Session, carrier_id: int) -> Optional[AssistantDB]:
    """
    Finds an assistant record assigned to a specific carrier ID.

    Args:
        db: The active SQLAlchemy session.
        carrier_id: The ID of the carrier the assistant is linked to.

    Returns:
        The AssistantDB object if found, otherwise None.
    """
    # Query AssistantDB, filter by the foreign key carrier_id, get the first result or None
    return db.query(AssistantDB).filter(AssistantDB.carrier_id == carrier_id).first()


def find_carrier_by_mc_number(db: Session, mc_number: str) -> Optional[CarrierDB]:
    """
    Finds a single carrier record based on their MC number.

    Args:
        db: The active SQLAlchemy session.
        mc_number: The carrier's Motor Carrier number to search for.

    Returns:
        The CarrierDB object if found, otherwise None.
    """
    # Query CarrierDB, filter by mc_number, get the first result or None
    return db.query(CarrierDB).filter(CarrierDB.mc_number == mc_number).first()


def create_carrier(db: Session, mc_number: str, city: str, state: str, phone: str, agent_name: str) -> CarrierDB:
    """
    Creates a new carrier record in the database.

    Args:
        db: The active SQLAlchemy session.
        mc_number: Motor Carrier number.
        city: Carrier's city.
        state: Carrier's state.
        phone: Carrier's phone number.
        agent_name: Name of the agent associated with the carrier.

    Returns:
        The newly created CarrierDB object, refreshed with its database ID.
    """
    # Create a new CarrierDB object instance
    carrier = CarrierDB(
        mc_number=mc_number,
        city=city,
        state=state,
        country="USA",  # Assigns a default value
        phone=phone,
        agent_name=agent_name
    )
    # Add the new object to the session
    db.add(carrier)
    # Commit the transaction to save the record
    db.commit()
    # Refresh the object to load database-generated values (like the primary key ID)
    db.refresh(carrier)
    # Return the newly created object
    return carrier


def create_assistant(db: Session, twilio_number: str, region: str, carrier_id: int) -> AssistantDB:
    """
    Creates a new assistant record linked to a specific carrier.

    Args:
        db: The active SQLAlchemy session.
        twilio_number: The Twilio phone number assigned to the assistant.
        region: The region the assistant operates in.
        carrier_id: The ID of the carrier this assistant is linked to.

    Returns:
        The newly created AssistantDB object, refreshed with its database ID.
    """
    # Create a new AssistantDB object instance
    assistant = AssistantDB(
        twilio_number=twilio_number,
        region=region,
        carrier_id=carrier_id  # Sets the foreign key relationship
    )
    # Add the new object to the session
    db.add(assistant)
    # Commit the transaction to save the record
    db.commit()
    # Refresh the object to load database-generated values
    db.refresh(assistant)
    # Return the newly created object
    return assistant

# Placeholder comment indicating where more functions could be added
# Add other CRUD functions as needed (e.g., for ShippingRequirementsDB)
