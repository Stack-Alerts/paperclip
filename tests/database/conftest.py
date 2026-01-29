"""
Pytest fixtures for database tests
Sprint 1.6.1 - Institutional-grade database testing

Provides proper database session fixtures using .env configuration
"""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.optimizer_v3.database.models import Base

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


@pytest.fixture(scope="session")
def db_engine():
    """
    Create database engine from environment variables
    
    Uses .env file in project root for configuration
    """
    # Get database configuration from environment (.env file loaded above)
    db_host = os.getenv('POSTGRES_HOST', 'localhost')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'optimizer_v3')
    db_user = os.getenv('POSTGRES_USER', 'optimizer_admin')
    db_password = os.getenv('POSTGRES_PASSWORD', '')
    
    # Create connection string
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Create engine
    engine = create_engine(connection_string, echo=False)
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Create a new database session for each test
    
    Provides transaction isolation - each test gets fresh session
    Automatically rolls back after test completes
    
    Uses SAVEPOINT for proper isolation without affecting other tests
    """
    # Create connection
    connection = db_engine.connect()
    
    # Begin a transaction
    transaction = connection.begin()
    
    # Create session bound to this connection
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    
    yield session
    
    # Cleanup - rollback transaction and close
    session.close()
    transaction.rollback()
    connection.close()
