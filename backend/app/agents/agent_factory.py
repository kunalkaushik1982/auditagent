"""
Agent factory for creating agent instances.
File: backend/app/agents/agent_factory.py

Factory pattern for instantiating the correct agent based on type.
"""

from typing import Optional
from .base_agent import BaseAuditAgent
from .sow_reviewer import SoWReviewerAgent
from .project_plan_reviewer import ProjectPlanReviewerAgent
from .architecture_compliance_agent import ArchitectureComplianceAgent


class AgentFactory:
    """Factory class to create agent instances"""
    
    # Registry of available agents
    _agents = {
        "sow_reviewer": SoWReviewerAgent,
        "project_plan_reviewer": ProjectPlanReviewerAgent,
        "architecture_compliance": ArchitectureComplianceAgent
    }
    
    @classmethod
    def create_agent(cls, agent_type: str) -> Optional[BaseAuditAgent]:
        """
        Create an agent instance based on type.
        
        Args:
            agent_type: Type of agent to create
            
        Returns:
            Agent instance or None if type not found
        """
        agent_class = cls._agents.get(agent_type)
        if agent_class:
            return agent_class()
        return None
    
    @classmethod
    def get_available_agents(cls) -> list:
        """Get list of available agent types"""
        return [
            {
                "type": agent_type,
                "name": agent_class().agent_name
            }
            for agent_type, agent_class in cls._agents.items()
        ]
