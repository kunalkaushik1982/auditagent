"""
Notification database model.
File: backend/app/models/notification.py

Defines the Notification model for in-app notifications.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Notification(Base):
    """Notification model for in-app notifications"""
    
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Notification details
    notification_type = Column(String, nullable=False)  # audit_completed, audit_failed
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    related_session_id = Column(Integer, ForeignKey("audit_sessions.id"), nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    session = relationship("AuditSession")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.notification_type}', read={self.is_read})>"
