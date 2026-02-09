"""
Pydantic schemas for API request/response models.
File: backend/app/api/schemas.py

Defines all Pydantic models for API validation.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# Auth Schemas
class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Audit Schemas
class AuditSubmit(BaseModel):
    agent_type: str = Field(..., pattern="^(sow_reviewer|project_plan_reviewer|architecture_compliance)$")


class AuditStatusResponse(BaseModel):
    session_id: str
    status: str
    progress_percentage: float  # Changed to match DB field name
    agent_type: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class FindingResponse(BaseModel):
    id: int
    finding_type: str
    checklist_item: str
    description: str
    severity: Optional[str] = None
    location_in_document: Optional[str] = None
    recommendation: Optional[str] = None
    
    class Config:
        from_attributes = True


class AuditResultResponse(BaseModel):
    result_id: str
    session_id: int
    summary: Optional[str] = None
    validation_score: Optional[float] = None
    report_content: str
    findings: List[FindingResponse] = []
    created_at: datetime
    
    class Config:
        from_attributes = True


# Notification Schemas
class NotificationResponse(BaseModel):
    id: int
    notification_id: str
    notification_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int


# Agent Schemas
class AgentInfo(BaseModel):
    type: str
    name: str
    description: str
