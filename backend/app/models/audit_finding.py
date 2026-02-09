"""
Audit finding database model.
File: backend/app/models/audit_finding.py

Defines the AuditFinding model for individual audit issues/observations.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class AuditFinding(Base):
    """Individual audit finding or issue"""
    
    __tablename__ = "audit_findings"
    
    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(String, unique=True, index=True, nullable=False)
    result_id = Column(Integer, ForeignKey("audit_results.id"), nullable=False)
    
    # Finding details
    checklist_item = Column(Text, nullable=False)  # The requirement being checked
    finding_type = Column(String, nullable=False)  # missing, non_compliant, advisory, compliant
    severity = Column(String, nullable=True)  # For future: critical, high, medium, low
    description = Column(Text, nullable=False)
    location_in_document = Column(String, nullable=True)  # Section, page, line reference
    recommendation = Column(Text, nullable=True)
    
    # Relationships
    result = relationship("AuditResult", back_populates="findings")
    
    def __repr__(self):
        return f"<AuditFinding(id={self.id}, type='{self.finding_type}')>"
