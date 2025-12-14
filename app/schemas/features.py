"""
Pydantic schemas for feature prioritization
"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class FeaturePrioritizationRequest(BaseModel):
    """Request body for POST /v1/features/prioritize"""
    apple_user_id: str = Field(..., description="Apple user identifier", min_length=1)
    feature_code: str = Field(..., description="Feature code identifier", min_length=1, max_length=100)

    @field_validator('apple_user_id')
    @classmethod
    def validate_apple_user_id(cls, v: str) -> str:
        """Ensure apple_user_id is not empty"""
        if not v or not v.strip():
            raise ValueError("apple_user_id cannot be empty")
        return v.strip()

    @field_validator('feature_code')
    @classmethod
    def validate_feature_code(cls, v: str) -> str:
        """Ensure feature_code is not empty and normalized"""
        if not v or not v.strip():
            raise ValueError("feature_code cannot be empty")
        return v.strip().lower()  # Normalize to lowercase

    class Config:
        json_schema_extra = {
            "example": {
                "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
                "feature_code": "advanced_export_options"
            }
        }


class FeaturePrioritizationResponse(BaseModel):
    """Response body for POST /v1/features/prioritize"""
    apple_user_id: str = Field(..., description="Apple user identifier")
    feature_code: str = Field(..., description="Feature code identifier")
    counter: int = Field(..., description="Number of times this user has prioritized this feature")
    created: bool = Field(..., description="True if this is the first time user prioritized this feature")
    updated_at: datetime = Field(..., description="When the prioritization was last updated")

    class Config:
        json_schema_extra = {
            "example": {
                "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
                "feature_code": "advanced_export_options",
                "counter": 1,
                "created": True,
                "updated_at": "2025-12-13T10:30:00Z"
            }
        }
