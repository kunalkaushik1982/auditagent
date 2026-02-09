"""
Architecture Compliance Agent implementation.
File: backend/app/agents/architecture_compliance_agent.py

Agent for reviewing technical architecture documents.
"""

from typing import Dict, Any
from .base_agent import BaseAuditAgent
import logging

logger = logging.getLogger(__name__)


class ArchitectureComplianceAgent(BaseAuditAgent):
    """Agent specialized in reviewing architecture compliance documents"""
    
    def __init__(self):
        super().__init__(
            agent_name="Architecture Compliance Agent",
            agent_type="architecture_compliance"
        )
    
    async def process_artifact(
        self,
        artifact_path: str,
        checklist_path: str
    ) -> Dict[str, Any]:
        """
        Process architecture document against checklist.
        
        This uses the base class implementation which handles:
        - Document loading (PDF, Word, text)
        - Checklist validation
        - AI-powered analysis
        - Report generation
        
        The AI adapts to architecture-specific validation through
        the agent_name and agent_type context.
        
        Args:
            artifact_path: Path to the architecture document
            checklist_path: Path to the checklist file
            
        Returns:
            Dictionary with audit results, findings, and report
        """
        # The base class handles everything - we just need to be an architecture specialist
        # through our agent_name and agent_type which influence the AI's understanding
        return await super().process_artifact(artifact_path, checklist_path)
