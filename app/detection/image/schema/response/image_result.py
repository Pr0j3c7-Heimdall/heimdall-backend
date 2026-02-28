from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.schema.response import SuccessResponse

class C2PAResultSchema(BaseModel):
    c2pa_id: int = Field(..., description="C2PA verification result ID")
    is_c2pa_compliant: bool = Field(..., description="Whether the image is C2PA compliant")
    
    # 추가된 C2PA 필드들 (테이블 명세서 반영)
    created_model: Optional[str] = Field(None, description="생성 모델명 1")
    converted_model: Optional[str] = Field(None, description="생성 모델명 2")
    created_description: Optional[str] = Field(None, description="생성 모델명 3")
    claim_generator: Optional[str] = Field(None, description="서명한 주체 1")
    claim_generator_info_name: Optional[str] = Field(None, description="서명한 주체 2")
    synth_id: Optional[str] = Field(None, description="Google SynthID Watermark")
    visible_watermark: Optional[str] = Field(None, description="Google Visible Watermark")
    total_digital_source_type: Optional[str] = Field(None, description="디지털 콘텐츠 제작 방식 라벨")
    synth_id_digital_source_type: Optional[str] = Field(None, description="synthID 생성 방식 라벨")
    visible_watermark_digital_source_type: Optional[str] = Field(None, description="visible watermark 생성 방식 라벨")

    class Config:
        from_attributes = True

class BinaryResultSchema(BaseModel):
    binary_id: int = Field(..., description="Binary detection result ID")
    detection_method: str = Field(..., description="Method used for binary detection")
    confidence_score: Optional[float] = Field(None, description="Confidence score for this detection")
    result_json: Optional[Any] = Field(None, description="상세 결과 JSON")

    class Config:
        from_attributes = True

class MultiResultSchema(BaseModel):
    multi_id: int = Field(..., description="Multiclass detection result ID")
    detection_method: str = Field(..., description="Method used for multiclass detection")
    predicted_model: Optional[str] = Field(None, description="Predicted generator model")
    confidence_score: Optional[float] = Field(None, description="Confidence score for this prediction")
    result_json: Optional[Any] = Field(None, description="상세 결과 JSON")

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
