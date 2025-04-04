"""This code provides a structured way to:

Connect to a database specified in your settings.
Manage database sessions (units of work/transactions).
Initialize the database by creating tables based on your SQLAlchemy models.
Provide database sessions reliably to different parts of your application (specifically FastAPI routes and potentially other code)."""

# Import necessary components from SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Session is renamed to avoid potential naming conflicts

# Import standard Python library for creating context managers ('with' statements)
from contextlib import contextmanager
# Import Generator type hint for function signatures
from typing import Generator

# --- Configuration and Model Imports ---
# Assumes you have a 'config.py' with a 'settings' object containing DATABASE_URL
from config import settings
# Assumes you have a 'models.py' where your SQLAlchemy models inherit from a common Base
# '.' indicates a relative import from the current package/directory
from .models import Base

# --- Database Engine Setup ---
# Create the core interface to the database. The engine manages connection pooling.
engine = create_engine(
    settings.DATABASE_URL,    # The database connection string (e.g., "sqlite:///./sql_app.db", "postgresql://user:password@host/db")
    connect_args={"check_same_thread": False}, # Specific argument for SQLite. Allows multiple threads (like in a web server) to use the same connection. Not needed/used for other DBs like PostgreSQL.
    echo=True                   # Logs all SQL statements issued by SQLAlchemy to the console. Useful for debugging, usually False in production.
)

# --- Session Factory Setup ---
# Create a factory that will generate new Session objects when called.
# Sessions are the primary interface for interacting with the database (queries, adding/deleting data).
SessionLocal = sessionmaker(
    autocommit=False, # Transactions are NOT automatically committed. You must call db.commit() explicitly. This is standard practice.
    autoflush=False,  # Session does NOT automatically flush changes to the DB before queries. Helps control when SQL is issued. db.commit() implies a flush.
    bind=engine       # Tells the session factory which engine to use for creating connections.
)

# --- Database Initialization Function ---
def init_db():
    """
    Initializes the database.
    This function should be called once when your application starts (if needed).
    It creates all tables defined in your models that inherit from 'Base'
    if they don't already exist in the database.
    """
    # IMPORTANT: Ensure all your SQLAlchemy model modules are imported *before* calling create_all.
    # This is necessary so that the models register themselves with the Base metadata.
    # The relative import '.' assumes models.py is in the same directory or a subdirectory.
    from . import models # Example: If you have models in 'app/models/user.py' and 'app/models/item.py', importing 'app.models' might be enough if they import Base correctly.

    # Create all tables stored in Base.metadata. This issues "CREATE TABLE IF NOT EXISTS..." statements.
    Base.metadata.create_all(bind=engine)
    print("Database initialized and tables created (if not existing).")

# --- FastAPI Dependency for Database Sessions ---
def get_db() -> Generator[SQLAlchemySession, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy database session.

    Usage in a FastAPI route:
        @app.get("/items/")
        def read_items(db: SQLAlchemySession = Depends(get_db)):
            # Use 'db' here to query the database
            items = db.query(models.Item).all()
            return items

    This pattern ensures:
    1. A session is created for each request.
    2. The session is available within the route function.
    3. The session is *always* closed after the request finishes, releasing the connection.
       (Commit/rollback logic must be handled *within* the route function itself).
    """
    # Create a new session instance using the factory
    db = SessionLocal()
    try:
        # Yield the session to the calling function (the FastAPI route handler)
        # The code in the 'with' block or the route function executes here.
        yield db
    finally:
        # This block always executes after the 'yield', whether the route succeeded or raised an error.
        # Close the session to release the database connection back to the pool.
        db.close()

# --- Optional: Context Manager for Sessions Outside FastAPI ---
@contextmanager # Decorator to turn the generator function into a usable context manager
def DatabaseSession() -> Generator[SQLAlchemySession, None, None]:
    """
    Provides a database session using a context manager ('with' statement).
    Handles commit/rollback and closing automatically.

    Usage:
        with DatabaseSession() as db:
            # Use 'db' to perform database operations
            new_user = User(name="example")
            db.add(new_user)
            # Commit happens automatically if no exception occurs
            # Rollback happens automatically if an exception occurs

    Useful for scripts, background tasks, or testing where FastAPI's dependency injection isn't used.
    """
    # Create a new session instance
    db = SessionLocal()
    try:
        # Yield the session to the code inside the 'with' block
        yield db
        # If the 'with' block completes without raising an exception, commit the transaction.
        db.commit()
    except Exception:
        # If any exception occurs within the 'with' block, rollback the transaction.
        db.rollback()
        # Re-raise the exception so it's not silently ignored.
        raise
    finally:
        # Always close the session, regardless of success or failure.
        db.close()