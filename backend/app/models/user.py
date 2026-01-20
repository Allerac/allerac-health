from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # NULL se OAuth
    name = Column(String(255), nullable=True)
    avatar_url = Column(String, nullable=True)
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'github'
    oauth_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    garmin_credentials = relationship("GarminCredentials", back_populates="user", uselist=False)
    sync_jobs = relationship("SyncJob", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"
