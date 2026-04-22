from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models import AckStatus


class DocumentOut(BaseModel):
    id: int
    title: str
    original_filename: str
    mime_type: str
    share_token: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class UserInfo(BaseModel):
    username: str
    full_name: str
    department: str
    email: str


class DocumentLogOut(BaseModel):
    id: int
    ad_username: Optional[str]
    full_name: Optional[str]
    department: Optional[str]
    email: Optional[str]
    status: AckStatus
    opened_at: datetime
    confirmed_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    ip_address: Optional[str]

    model_config = {"from_attributes": True}


class ConfirmRequest(BaseModel):
    pass


class AcknowledgeRequest(BaseModel):
    pass


class IdentifyResponse(BaseModel):
    identified: bool
    user: Optional[UserInfo] = None
    status: Optional[AckStatus] = None
