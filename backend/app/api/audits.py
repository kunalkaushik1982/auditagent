"""
Audit management API endpoints.
File: backend/app/api/audits.py

Handles audit submission, status tracking, and result retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from datetime import datetime
import json

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.models.audit_session import AuditSession
from backend.app.models.audit_result import AuditResult
from backend.app.models.audit_finding import AuditFinding as DBFinding
from backend.app.api.dependencies import get_current_user
from backend.app.api.schemas import AuditStatusResponse, AuditResultResponse, FindingResponse
from backend.app.agents.agent_factory import AgentFactory
from backend.app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_audit(
    agent_type: str = Form(..., regex="^(sow_reviewer|project_plan_reviewer|architecture_compliance)$"),
    artifact_file: UploadFile = File(...),
    checklist_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a new audit request.
    
    Uploads artifact and checklist, creates audit session, and processes immediately.
    Note: In production with Celery, this would queue the task. For now, runs synchronously.
    """
    try:
        # Generate session ID
        session_id_str = str(uuid.uuid4())
        
        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Save uploaded files
        artifact_path = os.path.join(settings.UPLOAD_DIR, f"{session_id_str}_artifact_{artifact_file.filename}")
        checklist_path = os.path.join(settings.UPLOAD_DIR, f"{session_id_str}_checklist_{checklist_file.filename}")
        
        with open(artifact_path, "wb") as f:
            f.write(await artifact_file.read())
        
        with open(checklist_path, "wb") as f:
            f.write(await checklist_file.read())
        
        logger.info(f"Files uploaded for session {session_id_str}")
        
        # Create audit session in database (status=pending for Celery)
        audit_session = AuditSession(
            session_id=session_id_str,
            user_id=current_user.id,
            agent_type=agent_type,
            artifact_path=artifact_path,
            artifact_filename=artifact_file.filename,
            checklist_path=checklist_path,
            checklist_filename=checklist_file.filename,
            status="pending",  # Changed from "processing" - Celery will update
            progress_percentage=0.0,
            started_at=datetime.utcnow()
        )
        
        db.add(audit_session)
        db.commit()
        db.refresh(audit_session)
        
        # Queue the audit processing task with Celery
        from backend.app.tasks import process_audit_task
        task = process_audit_task.delay(session_id_str)
        logger.info(f"🚀 Audit {session_id_str} queued with task ID: {task.id}")
        
        return {
            "session_id": session_id_str,
            "status": "pending",
            "message": "Audit queued for processing",
            "task_id": task.id
        }
            
    except Exception as e:
        logger.error(f"Error submitting audit: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting audit: {str(e)}"
        )


@router.get("/status/{session_id}", response_model=AuditStatusResponse)
async def get_audit_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the status of an audit session"""
    
    # Find the session
    audit_session = db.query(AuditSession).filter(
        AuditSession.session_id == session_id,
        AuditSession.user_id == current_user.id
    ).first()
    
    if not audit_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit session not found"
        )
    
    return audit_session


@router.get("/results/{session_id}", response_model=AuditResultResponse)
async def get_audit_results(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the results of a completed audit"""
    
    # Find the session
    audit_session = db.query(AuditSession).filter(
        AuditSession.session_id == session_id,
        AuditSession.user_id == current_user.id
    ).first()
    
    if not audit_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit session not found"
        )
    
    if audit_session.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audit is not completed yet. Current status: {audit_session.status}"
        )
    
    # Get the result
    if not audit_session.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit result not found"
        )
    
    # Convert findings to response format
    findings_response = [
        FindingResponse(
            id=f.id,
            finding_type=f.finding_type,
            checklist_item=f.checklist_item,
            description=f.description,
            severity=f.severity,
            location_in_document=f.location_in_document,
            recommendation=f.recommendation
        )
        for f in audit_session.result.findings
    ]
    
    return AuditResultResponse(
        result_id=audit_session.result.result_id,
        session_id=audit_session.session_id,
        audit_number=audit_session.id,
        summary=audit_session.result.summary,
        validation_score=audit_session.result.validation_score,
        report_content=audit_session.result.report_content,
        annotated_artifact_path=audit_session.result.annotated_artifact_path,
        findings=findings_response,
        created_at=audit_session.result.created_at
    )


@router.get("/my-audits")
async def get_my_audits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all audit sessions for the current user"""
    
    sessions = db.query(AuditSession).filter(
        AuditSession.user_id == current_user.id
    ).order_by(AuditSession.created_at.desc()).all()
    
    return {
        "audits": [
            {
                "session_id": s.session_id,
                "audit_number": s.id,
                "agent_type": s.agent_type,
                "status": s.status,
                "progress_percentage": s.progress_percentage,  # Fixed: was "progress"
                "created_at": s.created_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "duration_seconds": (
                    (s.completed_at - s.created_at).total_seconds() 
                    if s.completed_at else None
                ),
                "error_message": s.error_message if s.status == "failed" else None
            }
            for s in sessions
        ]
    }


@router.get("/results/{session_id}/download-annotated")
async def download_annotated_report(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Download the annotated Word document"""
    
    audit_session = db.query(AuditSession).filter(
        AuditSession.session_id == session_id
    ).first()
    
    if not audit_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit session not found"
        )
        
    if not audit_session.result or not audit_session.result.annotated_artifact_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No annotated report available"
        )
        
    file_path = audit_session.result.annotated_artifact_path
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotated file missing from server"
        )
        
    filename = os.path.basename(file_path)
    
    # Determine media type
    media_type = 'application/octet-stream'
    if filename.lower().endswith('.docx'):
        media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif filename.lower().endswith('.pdf'):
        media_type = 'application/pdf'
        
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )
