"""
SoW Reviewer Agent implementation.
File: backend/app/agents/sow_reviewer.py

Agent for reviewing Statement of Work documents.
"""

from typing import Dict, Any, List
import json
from datetime import datetime
from .base_agent import BaseAuditAgent, AuditFinding
import logging

logger = logging.getLogger(__name__)


class SoWReviewerAgent(BaseAuditAgent):
    """Agent specialized in reviewing Statement of Work documents"""
    
    def __init__(self):
        super().__init__(
            agent_name="SoW Reviewer Agent",
            agent_type="sow_reviewer"
        )
