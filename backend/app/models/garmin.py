from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, LargeBinary, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class GarminCredentials(Base):
    __tablename__ = "garmin_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    email_encrypted = Column(LargeBinary, nullable=False)
    password_encrypted = Column(LargeBinary, nullable=True)
    oauth1_token_encrypted = Column(LargeBinary, nullable=True)
    oauth2_token_encrypted = Column(LargeBinary, nullable=True)
    is_connected = Column(Boolean, default=False)
    mfa_pending = Column(Boolean, default=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String, nullable=True)
    sync_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="garmin_credentials")

    def __repr__(self):
        return f"<GarminCredentials user_id={self.user_id}>"


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    status = Column(String(50), nullable=False, default="pending")
    job_type = Column(String(50), nullable=False, default="full")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    records_fetched = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    job_metadata = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="sync_jobs")

    def __repr__(self):
        return f"<SyncJob {self.id} status={self.status}>"


class MFASession(Base):
    __tablename__ = "mfa_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    garmin_email = Column(String(255), nullable=False)
    session_data = Column(LargeBinary, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<MFASession user_id={self.user_id}>"
