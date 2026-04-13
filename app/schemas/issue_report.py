"""
Pydantic schemas for issue report submission
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# Patterns to reject — basic injection / XSS defence
_SCRIPT_PATTERN = re.compile(r"<script", re.IGNORECASE)
_SQL_INJECTION_PATTERNS = [
    re.compile(r"';\s*DROP\s", re.IGNORECASE),
    re.compile(r"UNION\s+SELECT", re.IGNORECASE),
    re.compile(r"--\s"),
]
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_NULL_BYTE = "\x00"

# Basic email format check
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Valid area keys
_VALID_AREAS = {"home", "activity", "repository", "utilities", "settings", "account", "credits", "other"}


def _sanitize_string(value: str) -> str:
    """Strip HTML tags and null bytes from a string."""
    value = value.replace(_NULL_BYTE, "")
    value = _HTML_TAG_PATTERN.sub("", value)
    return value.strip()


def _reject_injection(value: str, field_name: str) -> None:
    """Raise ValueError if the string contains injection patterns."""
    if _NULL_BYTE in value:
        raise ValueError(f"{field_name} contains invalid characters")
    if _SCRIPT_PATTERN.search(value):
        raise ValueError(f"{field_name} contains disallowed content")
    for pattern in _SQL_INJECTION_PATTERNS:
        if pattern.search(value):
            raise ValueError(f"{field_name} contains disallowed content")


class IssueReportRequest(BaseModel):
    """Request body for POST /v1/events/issue-report"""
    apple_user_id: Optional[str] = Field(None, description="Apple user identifier (nullable for anonymous)")
    device_id: Optional[str] = Field(None, description="UIDevice.identifierForVendor")
    area: str = Field(..., description="App area/tab key", min_length=1, max_length=50)
    feature: Optional[str] = Field(None, description="Feature within the area", max_length=100)
    description: str = Field(..., description="User's issue description", min_length=20, max_length=2000)
    contact_email: Optional[str] = Field(None, description="Optional follow-up email", max_length=255)
    app_version: Optional[str] = Field(None, description="App version")
    app_build: Optional[str] = Field(None, description="App build number")
    device_profile: Optional[Dict[str, Any]] = Field(None, description="Device snapshot for debugging")
    captured_at: datetime = Field(..., description="When the user submitted on-device")

    @field_validator('area')
    @classmethod
    def validate_area(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in _VALID_AREAS:
            raise ValueError(f"area must be one of: {', '.join(sorted(_VALID_AREAS))}")
        return v

    @field_validator('feature')
    @classmethod
    def validate_feature(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        _reject_injection(v, "feature")
        v = _sanitize_string(v)
        if not v:
            return None
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        _reject_injection(v, "description")
        v = _sanitize_string(v)
        if len(v) < 20:
            raise ValueError("description must be at least 20 characters after sanitization")
        if len(v) > 2000:
            v = v[:2000]
        return v

    @field_validator('contact_email')
    @classmethod
    def validate_contact_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        v = v.strip()
        if not _EMAIL_REGEX.match(v):
            raise ValueError("contact_email must be a valid email address")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
                "device_id": "E621E1F8-C36C-495A-93FC-0C247A3E6E5F",
                "area": "home",
                "feature": "Search & Filters",
                "description": "The search bar doesn't respond when I type quickly. I have to wait a few seconds between keystrokes.",
                "contact_email": "user@example.com",
                "app_version": "2.0.0",
                "app_build": "142",
                "captured_at": "2026-04-13T10:30:00Z"
            }
        }


class IssueReportResponse(BaseModel):
    """Response body for POST /v1/events/issue-report"""
    report_id: str = Field(..., description="Server-assigned report ID")
    logged: bool = Field(..., description="Whether the report was logged")
    logged_at: datetime = Field(..., description="Server timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "logged": True,
                "logged_at": "2026-04-13T10:30:01Z"
            }
        }
