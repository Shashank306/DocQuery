# database.py
from typing import Generator
from sqlmodel import SQLModel, Session, create_engine, text
from app.core.config import settings
from app.core.logging_simple import logger

sync_engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    echo=settings.DB_ECHO,
)

def init_db() -> None:
    try:
        # Import all models to ensure they're registered
        from app.models.db import User, UserQuery, UserDocument, UserSession  # noqa: F401
        
        logger.info("Creating database tables...")
        SQLModel.metadata.create_all(sync_engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def get_session() -> Generator[Session, None, None]:
    """Get synchronous database session."""
    with Session(sync_engine) as session:
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

def check_db_health() -> bool:
    """Check database connectivity for health checks."""
    try:
        with Session(sync_engine) as session:
            result = session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
