"""
Audit session database model.
File: backend/app/models/audit_session.py

Defines the AuditSession model for tracking audit requests.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class AuditSession(Base):
    """Audit session model to track individual audit requests"""
    
    __tablename__ = "audit_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Agent and files
    agent_type = Column(String, nullable=False)  # sow_reviewer, project_plan, architecture
    artifact_filename = Column(String, nullable=False)
    artifact_path = Column(String, nullable=False)
    checklist_filename = Column(String, nullable=False)
    checklist_path = Column(String, nullable=False)
    
    # Status tracking
    status = Column(String, default="pending")  # pending, running, completed, failed
    task_id = Column(String, nullable=True)  # Celery task ID
    progress_percentage = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    priority = Column(Integer, default=0)  # For future priority queue
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_sessions")
    result = relationship("AuditResult", back_populates="session", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AuditSession(id={self.id}, status='{self.status}', agent='{self.agent_type}')>"
