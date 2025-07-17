#!/usr/bin/env python3
"""
Database initialization script for RAG Hybrid System.
Creates tables and optionally seeds initial data.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import uuid
from datetime import datetime
from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings
from app.models.db import User, UserDocument, UserQuery, UserSession
from app.auth.security import get_password_hash

async def init_db():
    """Initialize the database with tables and optionally seed data."""
    engine = create_engine(settings.DATABASE_URL, echo=True)
    
    # Create all tables
    SQLModel.metadata.create_all(engine)
    print("✅ Database tables created successfully")
    
    # Optionally create a test user
    if settings.ENVIRONMENT == "development":
        with Session(engine) as session:
            # Check if admin user exists
            from sqlmodel import select
            statement = select(User).where(User.email == 'admin@example.com')
            existing_user = session.exec(statement).first()
            
            if not existing_user:
                admin_user = User(
                    email="admin@example.com",
                    username="admin",
                    full_name="System Administrator",
                    hashed_password=get_password_hash("admin123"),
                    is_active=True,
                    is_verified=True,
                    role="admin"
                )
                session.add(admin_user)
                session.commit()
                print("✅ Created admin user: admin@example.com / admin123")
            else:
                print("ℹ️  Admin user already exists")

if __name__ == "__main__":
    asyncio.run(init_db())
