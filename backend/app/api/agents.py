"""
Agent information API endpoints.
File: backend/app/api/agents.py

Provides information about available agents.
"""

from fastapi import APIRouter
from typing import List, Dict

# TODO: Import AgentFactory
# from backend.app.agents import AgentFactory

router = APIRouter()


@router.get("/available")
async def get_available_agents() -> List[Dict[str, str]]:
    """
    Get list of available audit agents.
    
    TODO: Implement using AgentFactory
    - Return list of agent types and names
    """
    # Placeholder response
    return [
        {
            "type": "sow_reviewer",
            "name": "SoW Reviewer Agent",
            "description": "Reviews Statement of Work documents"
        },
        {
            "type": "project_plan_reviewer",
            "name": "Project Plan Reviewer Agent",
            "description": "Reviews project plan documents"
        },
        {
            "type": "architecture_compliance",
            "name": "Architecture Compliance Agent",
            "description": "Reviews architecture for compliance"
        }
    ]


@router.get("/{agent_type}/info")
async def get_agent_info(agent_type: str):
    """
    Get detailed information about a specific agent.
    
    TODO: Implement agent info retrieval
    - Validate agent_type
    - Return agent capabilities and requirements
    """
    pass
