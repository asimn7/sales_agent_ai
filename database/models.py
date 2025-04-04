"""
Overall Purpose:

This code defines the structure of your database tables using Python classes
via SQLAlchemy's declarative mapping system. 
Each class corresponds to a table in your database, 
and the attributes within each class (defined using Column)
correspond to the columns in that table. SQLAlchemy uses these definitions to:

Interact with the database (querying, inserting, updating, deleting data) 
using Python objects instead of raw SQL.
Potentially create the database schema (tables) using tools
like Alembic or Base.metadata.create_all().
"""
import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func # For default timestamps

# Create the base class for declarative models
Base = declarative_base()

class PersonalInfoDB(Base):
    """Stores personal information linked to phone calls."""
    __tablename__ = "personal_info"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    call_sid = Column(String, unique=True, nullable=True) # Can be updated per call
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship (optional, if needed)
    # conversations = relationship("ConversationDB", back_populates="caller_info")

class CarrierDB(Base):
    """Stores information about trucking carriers."""
    __tablename__ = "carriers"

    id = Column(Integer, primary_key=True, index=True)
    mc_number = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True) # Added name field based on crewai task
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False, default="USA")
    region = Column(String, nullable=True) # Potentially derived from city/state
    phone = Column(String, unique=True, nullable=False) # Assigned Twilio number
    agent_name = Column(String, nullable=True) # Assigned agent identifier
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    assistant = relationship("AssistantDB", back_populates="carrier", uselist=False) # One-to-one

class AssistantDB(Base):
    """Stores information about assigned AI assistants (Twilio numbers)."""
    __tablename__ = "assistants"

    id = Column(Integer, primary_key=True, index=True)
    twilio_number = Column(String, unique=True, nullable=False)
    region = Column(String, nullable=True) # Region the number serves
    carrier_id = Column(Integer, ForeignKey("carriers.id"), unique=True) # Link to one carrier
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    carrier = relationship("CarrierDB", back_populates="assistant")

class ConversationDB(Base):
    """Stores transcripts and context of conversations."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True, nullable=False)
    # Optional: Link to PersonalInfoDB if desired
    # caller_id = Column(Integer, ForeignKey("personal_info.id"))
    transcript = Column(Text, nullable=False)
    system_message = Column(Text, nullable=True) # System prompt used for this convo
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship (optional)
    # caller_info = relationship("PersonalInfoDB", back_populates="conversations")


# Add other models like ShippingRequirementsDB if needed, following the same pattern
class ShippingRequirementsDB(Base):
     __tablename__ = "shipping_requirements"
     id = Column(Integer, primary_key=True, index=True)
     # Add relevant fields
     placeholder = Column(String) # Example field

# You can add more models here...