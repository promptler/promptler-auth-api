"""
Monetization event database model
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Index, ForeignKey
from app.database import Base


def _utc_now():
    """Return current UTC time without timezone info for database storage"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MonetizationEvent(Base):
    """
    Monetization event from iOS app — purchases, credits, paywall interactions.
    Linked to users via apple_user_id (nullable for anonymous events).
    """
    __tablename__ = "monetization_events"

    id = Column(String(36), primary_key=True)  # UUID
    apple_user_id = Column(
        String(255),
        ForeignKey("users.apple_user_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    device_id = Column(String(255), nullable=True, index=True)
    event_name = Column(String(100), nullable=False, index=True)
    parameters = Column(JSON, nullable=True)
    app_version = Column(String(50), nullable=True)
    app_build = Column(String(50), nullable=True)
    captured_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utc_now)

    __table_args__ = (
        Index('idx_monetization_event_captured', 'event_name', 'captured_at'),
        Index('idx_monetization_user_captured', 'apple_user_id', 'captured_at'),
    )

    def __repr__(self):
        return f"<MonetizationEvent(id={self.id}, event={self.event_name}, user={self.apple_user_id})>"
