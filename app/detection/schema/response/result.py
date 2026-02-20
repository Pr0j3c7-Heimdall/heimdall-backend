from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.schema.response import SuccessResponse

class C2PAResultSchema(BaseModel):
    c2pa_id: int = Field(..., description="C2PA verification result ID")
    is_c2pa_compliant: bool = Field(..., description="Whether the image is C2PA compliant")
    signature_status: Optional[str] = Field(None, description="Signature status (e.g., valid, invalid, missing)")
    generator_model: Optional[str] = Field(None, description="Generator model from C2PA metadata")
    requires_ai_inference: bool = Field(..., description="Whether the image requires further AI inference")

    class Config:
        from_attributes = True

class BinaryResultSchema(BaseModel):
    binary_id: int = Field(..., description="Binary detection result ID")
    detection_method: str = Field(..., description="Method used for binary detection")
    is_detected: Optional[bool] = Field(None, description="Whether AI was detected by this method")
    confidence_score: Optional[float] = Field(None, description="Confidence score for this detection")

    class Config:
        from_attributes = True

class MultiResultSchema(BaseModel):
    multi_id: int = Field(..., description="Multiclass detection result ID")
    detection_method: str = Field(..., description="Method used for multiclass detection")
    predicted_model: Optional[str] = Field(None, description="Predicted generator model")
    confidence_score: Optional[float] = Field(None, description="Confidence score for this prediction")

    class Config:
        from_attributes = True

class DetectionResultData(BaseModel):
    image_id: int = Field(..., description="Image ID")
    image_url: str = Field(..., description="Original image URL")
    final_is_ai: Optional[bool] = Field(None, description="Final determination if the image is AI-generated")
    final_ai_probability: Optional[float] = Field(None, description="Final probability that the image is AI-generated")
    final_generator_model: Optional[str] = Field(None, description="Final identified generator model")
    completed_at: Optional[datetime] = Field(None, description="Time when the analysis was completed")
    c2pa: Optional[C2PAResultSchema] = Field(None, description="C2PA verification result")
    binary: List[BinaryResultSchema] = Field(default_factory=list, description="List of binary detection results")
    multi: List[MultiResultSchema] = Field(default_factory=list, description="List of multiclass detection results")

class DetectionResultResponse(SuccessResponse):
    data: DetectionResultData
