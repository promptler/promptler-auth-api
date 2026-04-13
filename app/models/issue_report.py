"""
Issue report database model
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Index, ForeignKey
from app.database import Base


def _utc_now():
    """Return current UTC time without timezone info for database storage"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class IssueReport(Base):
    """
    User-submitted issue report from the iOS app.
    Linked to users via apple_user_id (nullable for anonymous reports).
    """
    __tablename__ = "issue_reports"

    id = Column(String(36), primary_key=True)  # UUID
    apple_user_id = Column(
        String(255),
        ForeignKey("users.apple_user_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    device_id = Column(String(255), nullable=True)
    area = Column(String(50), nullable=False)
    feature = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    contact_email = Column(String(255), nullable=True)
    app_version = Column(String(50), nullable=True)
    app_build = Column(String(50), nullable=True)
    device_profile = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="new")
    captured_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utc_now)

    __table_args__ = (
        Index('idx_issue_report_user_captured', 'apple_user_id', 'captured_at'),
        Index('idx_issue_report_status_created', 'status', 'created_at'),
        Index('idx_issue_report_area_created', 'area', 'created_at'),
    )

    def __repr__(self):
        return f"<IssueReport(id={self.id}, area={self.area}, status={self.status}, user={self.apple_user_id})>"
