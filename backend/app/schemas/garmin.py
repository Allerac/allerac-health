from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class GarminConnect(BaseModel):
    """Schema para conectar conta Garmin."""
    email: EmailStr
    password: str


class GarminMFA(BaseModel):
    """Schema para enviar codigo MFA."""
    mfa_code: str


class GarminStatus(BaseModel):
    """Status da conexao Garmin."""
    is_connected: bool
    mfa_pending: bool
    last_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    sync_enabled: bool = True
    message: Optional[str] = None  # Message to show user (e.g., "Check your email for MFA code")


class GarminDisconnect(BaseModel):
    """Confirmacao para desconectar Garmin."""
    confirm: bool = False
