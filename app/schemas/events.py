"""
Pydantic schemas for monetization event tracking
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class MonetizationEventRequest(BaseModel):
    """Request body for POST /v1/events/monetization"""
    apple_user_id: Optional[str] = Field(None, description="Apple user identifier (nullable for anonymous)")
    device_id: Optional[str] = Field(None, description="UIDevice.identifierForVendor")
    event_name: str = Field(..., description="Event name (e.g., credits_purchased)", min_length=1, max_length=100)
    parameters: Optional[Dict[str, Any]] = Field(None, description="Event-specific parameters")
    app_version: Optional[str] = Field(None, description="App version")
    app_build: Optional[str] = Field(None, description="App build number")
    captured_at: datetime = Field(..., description="When event occurred on device")

    @field_validator('event_name')
    @classmethod
    def validate_event_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("event_name cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
                "device_id": "E621E1F8-C36C-495A-93FC-0C247A3E6E5F",
                "event_name": "credits_purchased",
                "parameters": {"pack_id": "credits_50", "amount": "4.99"},
                "app_version": "2.0.0",
                "app_build": "100",
                "captured_at": "2026-04-12T10:30:00Z"
            }
        }


class MonetizationEventResponse(BaseModel):
    """Response body for POST /v1/events/monetization"""
    event_id: str = Field(..., description="Server-assigned event ID")
    event_logged: bool = Field(..., description="Whether event was logged")
    logged_at: datetime = Field(..., description="Server timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "event_logged": True,
                "logged_at": "2026-04-12T10:30:01Z"
            }
        }
