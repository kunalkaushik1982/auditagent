"""
Database cleanup script - Remove old audit sessions except completed ones
Run from project root: python -m backend.cleanup_audits
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.database import SessionLocal
from backend.app.models.audit_session import AuditSession
from backend.app.models.audit_result import AuditResult
from backend.app.models.audit_finding import AuditFinding

def cleanup_audits():
    """Remove all audit sessions except completed ones"""
    db = SessionLocal()
    
    try:
        # Get all non-completed sessions
        sessions_to_delete = db.query(AuditSession).filter(
            AuditSession.status.in_(['pending', 'processing', 'failed'])
        ).all()
        
        print(f"Found {len(sessions_to_delete)} non-completed audit sessions to delete")
        
        for session in sessions_to_delete:
            print(f"Deleting session: {session.session_id} (status: {session.status})")
            
            # Delete associated results and findings first
            results = db.query(AuditResult).filter(
                AuditResult.session_id == session.id
            ).all()
            
            for result in results:
                # Delete findings
                db.query(AuditFinding).filter(
                    AuditFinding.result_id == result.id
                ).delete()
                
                # Delete result
                db.delete(result)
            
            # Delete session
            db.delete(session)
        
        db.commit()
        
        # Count remaining audits
        remaining = db.query(AuditSession).count()
        completed = db.query(AuditSession).filter(
            AuditSession.status == 'completed'
        ).count()
        
        print(f"\n✅ Cleanup complete!")
        print(f"Deleted: {len(sessions_to_delete)} sessions")
        print(f"Remaining: {remaining} sessions ({completed} completed)")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_audits()
