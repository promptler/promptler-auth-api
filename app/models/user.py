"""
User and device snapshot database models
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """
    User profile from Apple Sign-In
    """
    __tablename__ = "users"

    # Primary key: Apple user identifier
    apple_user_id = Column(String(255), primary_key=True, index=True)

    # User information (optional, only provided on first sign-in)
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)

    # Latest device profile (stored as JSON for flexibility)
    latest_device_profile = Column(JSON, nullable=True)

    # Timestamps
    first_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to device snapshots
    device_snapshots = relationship("DeviceSnapshot", back_populates="user", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_last_updated', 'last_updated_at'),
    )

    def __repr__(self):
        return f"<User(apple_user_id={self.apple_user_id}, email={self.email})>"


class DeviceSnapshot(Base):
    """
    Historical log of device profiles for each user
    """
    __tablename__ = "device_snapshots"

    id = Column(String(36), primary_key=True)  # UUID
    apple_user_id = Column(String(255), ForeignKey("users.apple_user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Device profile details
    device_model = Column(String(100), nullable=True)
    device_name = Column(String(255), nullable=True)
    system_name = Column(String(50), nullable=True)
    system_version = Column(String(50), nullable=True)
    locale = Column(String(10), nullable=True)
    region = Column(String(10), nullable=True)
    time_zone = Column(String(100), nullable=True)
    app_version = Column(String(50), nullable=True)
    app_build = Column(String(50), nullable=True)

    # Raw device profile JSON (for any additional fields)
    raw_profile = Column(JSON, nullable=True)

    # When this snapshot was captured
    captured_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="device_snapshots")

    # Indexes
    __table_args__ = (
        Index('idx_snapshot_user_captured', 'apple_user_id', 'captured_at'),
    )

    def __repr__(self):
        return f"<DeviceSnapshot(id={self.id}, user={self.apple_user_id}, captured_at={self.captured_at})>"
