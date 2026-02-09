"""
Audit result database model.
File: backend/app/models/audit_result.py

Defines the AuditResult model for storing audit outcomes.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class AuditResult(Base):
    """Audit result model to store audit findings and reports"""
    
    __tablename__ = "audit_results"
    
    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(String, unique=True, index=True, nullable=False)
    session_id = Column(Integer, ForeignKey("audit_sessions.id"), unique=True, nullable=False)
    
    # Results
    report_content = Column(Text, nullable=False)  # Detailed findings as JSON or markdown
    annotated_artifact_path = Column(String, nullable=True)  # Path to annotated document
    summary = Column(Text, nullable=True)  # High-level overview
    validation_score = Column(Float, nullable=True)  # Optional compliance score
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("AuditSession", back_populates="result")
    findings = relationship("AuditFinding", back_populates="result", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AuditResult(id={self.id}, session_id={self.session_id})>"
