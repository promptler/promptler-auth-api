"""
Feature prioritization tracking database model
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


def _utc_now():
    """Return current UTC time without timezone info for database storage"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FeaturePrioritization(Base):
    """
    Tracks user prioritization requests for features under construction
    """
    __tablename__ = "feature_prioritizations"

    # Primary key: UUID
    id = Column(String(36), primary_key=True)  # UUID

    # Foreign key to users
    apple_user_id = Column(String(255), ForeignKey("users.apple_user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Feature code identifier
    feature_code = Column(String(100), nullable=False, index=True)

    # Counter: increments each time user prioritizes this feature
    counter = Column(Integer, nullable=False, default=1)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=_utc_now)
    updated_at = Column(DateTime, nullable=False, default=_utc_now, onupdate=_utc_now)

    # Relationship
    user = relationship("User", backref="feature_prioritizations")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('apple_user_id', 'feature_code', name='uq_user_feature'),
        Index('idx_feature_code', 'feature_code'),
        Index('idx_feature_updated', 'updated_at'),
    )

    def __repr__(self):
        return f"<FeaturePrioritization(id={self.id}, user={self.apple_user_id}, feature={self.feature_code}, counter={self.counter})>"
