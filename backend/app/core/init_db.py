"""
Database initialization script.
File: backend/app/core/init_db.py

Creates all database tables and optionally seeds initial data.
"""

from sqlalchemy.orm import Session
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.core.security import hash_password
from backend.app.models import User, AuditSession, AuditResult, AuditFinding, Notification
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Initialize database by creating all tables.
    """
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully")
    except Exception as e:
        logger.error(f"✗ Error creating database tables: {e}")
        raise


def seed_initial_data() -> None:
    """
    Seed the database with initial data (admin user, etc.)
    """
    db = SessionLocal()
    try:
        # Check if admin user exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if not admin_user:
            logger.info("Creating default admin user...")
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hash_password("admin123"),
                is_active=True,
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            logger.info("✓ Admin user created (username: admin, password: admin123)")
        else:
            logger.info("✓ Admin user already exists")
            
    except Exception as e:
        logger.error(f"✗ Error seeding data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def reset_db() -> None:
    """
    Drop all tables and recreate them. USE WITH CAUTION!
    """
    try:
        logger.warning("⚠️  Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("✓ Tables dropped")
        
        logger.info("Creating fresh database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database reset complete")
    except Exception as e:
        logger.error(f"✗ Error resetting database: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        response = input("⚠️  This will DELETE ALL DATA. Are you sure? (yes/no): ")
        if response.lower() == "yes":
            reset_db()
            seed_initial_data()
        else:
            print("Reset cancelled")
    else:
        init_db()
        seed_initial_data()
