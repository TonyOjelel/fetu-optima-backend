from datetime import datetime
from pydantic import BaseModel, ConfigDict

class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,  # Allow ORM model parsing
        json_encoders={
            datetime: lambda dt: dt.isoformat()
        }
    )

class BaseAPIResponse(BaseSchema):
    """Base API response schema"""
    success: bool
    message: str | None = None
