"""
Celery Tasks for Audit Processing
File: backend/app/tasks.py

This contains the REAL audit processing task that uses OpenAI API.
For testing without API calls, use tasks_mock.py instead.
"""

import os
import asyncio
import time  # For artificial delays to demonstrate parallel processing
from datetime import datetime
import uuid
from celery import Task

# Import at function level to avoid circular import
def get_celery_app():
    from backend.app.celery_app import celery_app
    return celery_app

from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.audit_session import AuditSession
from backend.app.models.audit_result import AuditResult
from backend.app.models.audit_finding import AuditFinding as DBFinding
from backend.app.agents.sow_reviewer import SoWReviewerAgent
from backend.app.agents.project_plan_reviewer import ProjectPlanReviewerAgent
from backend.app.agents.architecture_compliance import ArchitectureComplianceAgent
import logging

logger = logging.getLogger(__name__)

# Get celery app
celery_app = get_celery_app()


class AuditTask(Task):
    """Custom task class with error handling"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Task {task_id} failed: {exc}", exc_info=einfo)

    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()


@celery_app.task(
    bind=True,
    base=AuditTask,
    name="backend.app.tasks.process_audit_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 2},
    time_limit=600,  # 10 minutes hard limit
    soft_time_limit=540  # 9 minutes soft limit
)
def process_audit_task(self, session_id: str):
    """
    Process an audit asynchronously.
    
    Args:
        session_id: The audit session ID to process
        
    Returns:
        dict: Processing result with status and result_id
    """
    db: Session = self.db
    
    try:
        logger.info(f"Starting audit processing for session {session_id}")
        
        # Get audit session from database
        audit_session = db.query(AuditSession).filter(
            AuditSession.session_id == session_id
        ).first()
        
        if not audit_session:
            raise ValueError(f"Audit session {session_id} not found")
        
        # Update status to processing
        audit_session.status = "processing"
        audit_session.progress_percentage = 0.0
        audit_session.started_at = datetime.utcnow()
        db.commit()
        
        # Update progress: Starting
        self.update_state(
            state='PROGRESS',
            meta={'progress': 5, 'status': 'Initializing agent...'}
        )
        
        # Create appropriate agent based on type
        agent_map = {
            'sow_reviewer': SoWReviewerAgent,
            'project_plan_reviewer': ProjectPlanReviewerAgent,
            'architecture_compliance': ArchitectureComplianceAgent
        }
        
        agent_class = agent_map.get(audit_session.agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {audit_session.agent_type}")
        
        agent = agent_class()
        
        audit_session.progress_percentage = 10.0
        db.commit()
        
        # Update progress: Loading files
        self.update_state(
            state='PROGRESS',
            meta={'progress': 10, 'status': 'Loading documents...'}
        )
        
        audit_session.progress_percentage = 30.0
        db.commit()
        
        # Process the audit
        logger.info(f"🚀 Processing audit with agent {audit_session.agent_type}")
        
        audit_session.progress_percentage = 50.0
        db.commit()
        logger.info(f"🤖 Running AI analysis...")
        
        # Note: Agent method is async, so we need to run it with asyncio
        # Celery tasks are synchronous, so we use asyncio.run()
        result = asyncio.run(agent.process_artifact(
            artifact_path=audit_session.artifact_path,
            checklist_path=audit_session.checklist_path
        ))
        
        # Update to 70%
        audit_session.progress_percentage = 70.0
        db.commit()
        
        logger.info(f"💾 Saving results...")
        
        # Update progress: Processing complete
        audit_session.progress_percentage = 90.0
        db.commit()
        
        self.update_state(
            state='PROGRESS',
            meta={'progress': 90, 'status': 'Saving results...'}
        )
        
        # Store results
        # Generate annotation if applicable (Word documents)
        annotated_path = None
        findings_list = result.get("findings", []) # Convert finding objects to dicts for annotator
        
        if audit_session.artifact_path.lower().endswith('.docx'):
            try:
                from backend.app.core.annotator import Annotator
                logger.info(f"🖊️ Generating inline annotations for {audit_session.artifact_path}")
                
                annotator = Annotator()
                annotated_path = annotator.annotate_document(
                    original_path=audit_session.artifact_path,
                    findings=findings_list
                )
            except Exception as e:
                logger.error(f"Failed to generate Word annotations: {e}")
                # Don't fail the whole audit if annotation fails
        elif audit_session.artifact_path.lower().endswith('.pdf'):
            try:
                from backend.app.core.annotator import Annotator
                logger.info(f"🖊️ Generating inline annotations for {audit_session.artifact_path}")
                
                annotator = Annotator()
                annotated_path = annotator.annotate_pdf(
                    original_path=audit_session.artifact_path,
                    findings=findings_list
                )
            except Exception as e:
                logger.error(f"Failed to generate PDF annotations: {e}")
                # Don't fail the whole audit if annotation fails
        
        result_id = str(uuid.uuid4())
        audit_result = AuditResult(
            result_id=result_id,
            session_id=audit_session.id,
            summary=result.get("summary", ""),
            validation_score=result.get("compliance_rate", 0.0),
            report_content=result.get("report", ""),
            annotated_artifact_path=annotated_path
        )
        db.add(audit_result)
        db.commit()
        
        # Store findings
        for finding_data in result.get("findings", []):
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
        
        db.commit()
        
        # Mark as completed
        audit_session.status = "completed"
        audit_session.progress_percentage = 100.0
        audit_session.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Audit {session_id} completed successfully")
        
        return {
            "status": "completed",
            "session_id": session_id,
            "result_id": result_id
        }
        
    except Exception as e:
        logger.error(f"Error processing audit {session_id}: {e}", exc_info=True)
        
        # Mark as failed
        if audit_session:
            audit_session.status = "failed"
            audit_session.error_message = str(e)
            audit_session.completed_at = datetime.utcnow()
            db.commit()
        
        # Re-raise exception for Celery to handle
        raise
