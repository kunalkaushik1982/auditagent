"""
Mock/Dummy Celery Task for Testing
File: backend/app/tasks_mock.py

This file contains a mock version of the audit processing task
that simulates the AI processing without making actual OpenAI API calls.
Use this for testing the Celery async flow.
"""

import time
import uuid
from datetime import datetime
from backend.app.celery_app import celery_app
from backend.app.core.database import SessionLocal
from backend.app.models.audit_session import AuditSession
from backend.app.models.audit_result import AuditResult
from backend.app.models.audit_finding import AuditFinding as DBFinding
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="backend.app.tasks_mock.process_audit_task_mock")
def process_audit_task_mock(self, session_id: str):
    """
    Mock audit processing task for testing.
    Simulates AI processing with dummy data and progress updates.
    
    Args:
        session_id: Session ID string
        
    Returns:
        Dict with status and result information
    """
    db = SessionLocal()
    
    try:
        logger.info(f"🧪 [MOCK] Starting audit processing for session: {session_id}")
        
        # Get audit session
        audit_session = db.query(AuditSession).filter(
            AuditSession.session_id == session_id
        ).first()
        
        if not audit_session:
            raise ValueError(f"Audit session {session_id} not found")
        
        # Update status to processing
        audit_session.status = "processing"
        audit_session.progress_percentage = 0.0
        db.commit()
        
        # Simulate processing with progress updates
        total_items = 41  # Simulating 41 checklist items
        findings = []
        
        for i in range(total_items):
            # Simulate processing time (1 second per item for visible progress)
            time.sleep(1)  # Increased from 0.2s to 1s = ~41 seconds total
            
            # Update progress
            progress = ((i + 1) / total_items) * 100
            audit_session.progress_percentage = progress
            db.commit()
            
            logger.info(f"🧪 [MOCK] Processing item {i+1}/{total_items} ({progress:.1f}%)")
            
            # Create mock finding
            finding_types = ["compliant", "non_compliant", "missing"]
            finding_type = finding_types[i % 3]  # Cycle through types
            
            findings.append({
                "finding_type": finding_type,
                "checklist_item": f"Mock Checklist Item #{i+1}: Sample requirement for testing",
                "description": f"Mock finding description for item {i+1}. This is simulated data for testing purposes.",
                "severity": "medium" if finding_type == "non_compliant" else "low",
                "location": f"Section {(i // 10) + 1}",
                "recommendation": f"Mock recommendation for item {i+1}" if finding_type != "compliant" else None
            })
        
        # Create audit result
        result_id_str = str(uuid.uuid4())
        compliant_count = sum(1 for f in findings if f["finding_type"] == "compliant")
        compliance_rate = (compliant_count / total_items) * 100
        
        audit_result = AuditResult(
            result_id=result_id_str,
            session_id=audit_session.id,
            report_content=f"""
# 🧪 Mock Audit Report

## Summary
This is a **mock audit report** generated for testing purposes.
No actual AI processing was performed.

## Statistics
- **Total Items**: {total_items}
- **Compliant**: {compliant_count}
- **Compliance Rate**: {compliance_rate:.1f}%

## Mock Findings
{len(findings)} mock findings were generated.
            """.strip(),
            summary=f"🧪 MOCK: Compliance Rate {compliance_rate:.1f}%",
            validation_score=float(compliance_rate)
        )
        
        db.add(audit_result)
        db.flush()
        
        # Create findings in database
        for finding_data in findings:
            finding = DBFinding(
                finding_id=str(uuid.uuid4()),
                result_id=audit_result.id,
                finding_type=finding_data["finding_type"],
                checklist_item=finding_data["checklist_item"],
                description=finding_data["description"],
                severity=finding_data.get("severity"),
                location_in_document=finding_data.get("location"),
                recommendation=finding_data.get("recommendation")
            )
            db.add(finding)
        
        # Mark as completed
        audit_session.status = "completed"
        audit_session.progress_percentage = 100.0
        audit_session.completed_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"🧪 [MOCK] Audit processing completed for session: {session_id}")
        
        return {
            "status": "completed",
            "session_id": session_id,
            "result_id": result_id_str,
            "compliance_rate": compliance_rate
        }
        
    except Exception as e:
        logger.error(f"🧪 [MOCK] Error processing audit: {e}", exc_info=True)
        
        # Update session with error
        if audit_session:
            audit_session.status = "failed"
            audit_session.error_message = f"Mock task error: {str(e)}"
            db.commit()
        
        raise
        
    finally:
        db.close()
