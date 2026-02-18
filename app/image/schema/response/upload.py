from pydantic import BaseModel, Field
from typing import Optional
from app.common.schema.response import SuccessResponse

class ImageUploadData(BaseModel):
    image_id: int = Field(..., description="Unique ID of the uploaded image")
    image_url: str = Field(..., description="Full URL to access the uploaded image")
    result: Optional[str] = Field(None, description="Result message from AI validation (if any)")

class ImageUploadResponse(SuccessResponse):
    data: ImageUploadData
