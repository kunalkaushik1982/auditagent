"""
Test script to simulate various failure scenarios
Run this to test error handling in the Celery implementation
"""

from backend.app.celery_app import celery_app
from backend.app.core.database import SessionLocal
from backend.app.models.audit_session import AuditSession
import time
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="backend.app.test_failures.simulate_failure")
def simulate_failure(self, session_id: str, failure_type: str = "none"):
    """
    Test task that simulates different failure scenarios
    
    Failure types:
    - "none": Normal successful execution
    - "early": Fails after 10% progress
    - "mid": Fails at 50% progress  
    - "late": Fails at 90% progress
    - "timeout": Infinite loop to test timeout
    - "db_error": Simulates database connection loss
    """
    db = SessionLocal()
    
    try:
        logger.info(f"🧪 Test task started: {failure_type} failure for {session_id}")
        
        # Get audit session
        audit_session = db.query(AuditSession).filter(
            AuditSession.session_id == session_id
        ).first()
        
        if not audit_session:
            raise ValueError(f"Session {session_id} not found")
        
        # Update to processing
        audit_session.status = "processing"
        audit_session.progress_percentage = 0.0
        db.commit()
        
        # Simulate processing with intentional failures
        for i in range(100):
            time.sleep(0.5)  # 50 seconds total
            
            progress = (i + 1)
            audit_session.progress_percentage = float(progress)
            db.commit()
            
            logger.info(f"Progress: {progress}%")
            
            # Trigger failure at specific points
            if failure_type == "early" and progress >= 10:
                raise Exception("🔥 Simulated early failure at 10%")
            
            if failure_type == "mid" and progress >= 50:
                raise Exception("🔥 Simulated mid-point failure at 50%")
            
            if failure_type == "late" and progress >= 90:
                raise Exception("🔥 Simulated late failure at 90%")
            
            if failure_type == "timeout":
                # Infinite loop to test timeout
                while True:
                    time.sleep(1)
            
            if failure_type == "db_error" and progress >= 30:
                # Simulate database error
                db.close()  # Close connection prematurely
                db.commit()  # This will fail
        
        # Success
        audit_session.status = "completed"
        audit_session.progress_percentage = 100.0
        audit_session.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ Test completed successfully")
        return {"status": "completed"}
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        
        # Update session with error
        if audit_session:
            audit_session.status = "failed"
            audit_session.error_message = str(e)
            try:
                db.commit()
            except:
                pass  # DB might be closed
        
        raise
        
    finally:
        try:
            db.close()
        except:
            pass


if __name__ == "__main__":
    # Manual test examples
    print("Test Failure Scenarios:")
    print("1. Normal: simulate_failure.delay('session-id', 'none')")
    print("2. Early fail: simulate_failure.delay('session-id', 'early')")
    print("3. Mid fail: simulate_failure.delay('session-id', 'mid')")
    print("4. Late fail: simulate_failure.delay('session-id', 'late')")
    print("5. DB error: simulate_failure.delay('session-id', 'db_error')")
    print("6. Timeout: simulate_failure.delay('session-id', 'timeout')")
