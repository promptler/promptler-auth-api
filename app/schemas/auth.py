"""
Pydantic schemas for Apple Sign-In authentication
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator


class DeviceProfile(BaseModel):
    """Device profile information from iOS app"""
    model: Optional[str] = Field(None, description="Device model (e.g., iPhone 14 Pro)")
    name: Optional[str] = Field(None, description="Device name (e.g., John's iPhone)")
    system_name: Optional[str] = Field(None, description="System name (e.g., iOS)")
    system_version: Optional[str] = Field(None, description="System version (e.g., 17.2)")
    locale: Optional[str] = Field(None, description="Locale identifier (e.g., en_US)")
    region: Optional[str] = Field(None, description="Region code (e.g., US)")
    time_zone: Optional[str] = Field(None, description="Time zone (e.g., America/New_York)")
    app_version: Optional[str] = Field(None, description="App version (e.g., 1.0.0)")
    app_build: Optional[str] = Field(None, description="App build number (e.g., 42)")

    class Config:
        json_schema_extra = {
            "example": {
                "model": "iPhone 14 Pro",
                "name": "John's iPhone",
                "system_name": "iOS",
                "system_version": "17.2",
                "locale": "en_US",
                "region": "US",
                "time_zone": "America/New_York",
                "app_version": "1.0.0",
                "app_build": "42"
            }
        }


class AppleSignInRequest(BaseModel):
    """Request body for POST /v1/auth/apple"""
    apple_user_id: str = Field(..., description="Apple user identifier (subject from token)", min_length=1)
    display_name: Optional[str] = Field(None, description="User's display name (only on first sign-in)")
    email: Optional[EmailStr] = Field(None, description="User's email (only on first sign-in)")
    device_profile: Optional[DeviceProfile] = Field(None, description="Device information")
    identity_token: Optional[str] = Field(None, description="Apple identity token (JWT) for verification")
    timestamp: datetime = Field(..., description="When this data was captured on the device")

    @field_validator('apple_user_id')
    @classmethod
    def validate_apple_user_id(cls, v: str) -> str:
        """Ensure apple_user_id is not empty"""
        if not v or not v.strip():
            raise ValueError("apple_user_id cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
                "display_name": "John Appleseed",
                "email": "john@privaterelay.appleid.com",
                "device_profile": {
                    "model": "iPhone 14 Pro",
                    "system_name": "iOS",
                    "system_version": "17.2",
                    "app_version": "1.0.0"
                },
                "identity_token": "eyJraWQiOiJBQkNERUZHSCIsImFsZyI6IlJTMjU2In0...",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class AppleSignInResponse(BaseModel):
    """Response body for POST /v1/auth/apple"""
    apple_user_id: str = Field(..., description="Apple user identifier")
    display_name: Optional[str] = Field(None, description="Stored display name")
    email: Optional[str] = Field(None, description="Stored email")
    latest_device_profile: Optional[Dict[str, Any]] = Field(None, description="Latest device profile")
    first_seen_at: datetime = Field(..., description="When user was first seen")
    last_updated_at: datetime = Field(..., description="When user was last updated")
    created: bool = Field(..., description="True if user was newly created, False if updated")

    class Config:
        json_schema_extra = {
            "example": {
                "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
                "display_name": "John Appleseed",
                "email": "john@privaterelay.appleid.com",
                "latest_device_profile": {
                    "model": "iPhone 14 Pro",
                    "system_name": "iOS"
                },
                "first_seen_at": "2024-01-15T10:30:00Z",
                "last_updated_at": "2024-01-15T10:30:00Z",
                "created": True
            }
        }


class DeviceUpdateRequest(BaseModel):
    """Request body for PATCH /v1/auth/apple/{identifier}"""
    device_profile: DeviceProfile = Field(..., description="Updated device information")
    timestamp: datetime = Field(..., description="When this data was captured on the device")

    class Config:
        json_schema_extra = {
            "example": {
                "device_profile": {
                    "model": "iPhone 14 Pro",
                    "system_version": "17.3",
                    "app_version": "1.0.1"
                },
                "timestamp": "2024-01-20T15:45:00Z"
            }
        }


class DeviceUpdateResponse(BaseModel):
    """Response body for PATCH /v1/auth/apple/{identifier}"""
    apple_user_id: str = Field(..., description="Apple user identifier")
    latest_device_profile: Optional[Dict[str, Any]] = Field(None, description="Updated device profile")
    last_updated_at: datetime = Field(..., description="When user was last updated")

    class Config:
        json_schema_extra = {
            "example": {
                "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
                "latest_device_profile": {
                    "model": "iPhone 14 Pro",
                    "system_version": "17.3"
                },
                "last_updated_at": "2024-01-20T15:45:00Z"
            }
        }


class OnlineModeEventRequest(BaseModel):
    """Request body for POST /v1/events/online-mode"""
    apple_user_id: str = Field(..., description="Apple user identifier", min_length=1)
    device_profile: Optional[DeviceProfile] = Field(None, description="Device information")
    timestamp: datetime = Field(..., description="When the online mode was activated")

    @field_validator('apple_user_id')
    @classmethod
    def validate_apple_user_id(cls, v: str) -> str:
        """Ensure apple_user_id is not empty"""
        if not v or not v.strip():
            raise ValueError("apple_user_id cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
                "device_profile": {
                    "model": "iPhone 14 Pro",
                    "system_version": "17.2",
                    "app_version": "1.0.0",
                    "app_build": "42"
                },
                "timestamp": "2024-01-20T15:45:00Z"
            }
        }


class OnlineModeEventResponse(BaseModel):
    """Response body for POST /v1/events/online-mode"""
    apple_user_id: str = Field(..., description="Apple user identifier")
    event_logged: bool = Field(..., description="Whether the event was successfully logged")
    logged_at: datetime = Field(..., description="When the event was logged on the server")

    class Config:
        json_schema_extra = {
            "example": {
                "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
                "event_logged": True,
                "logged_at": "2024-01-20T15:45:00Z"
            }
        }
