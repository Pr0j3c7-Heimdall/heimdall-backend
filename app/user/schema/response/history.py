from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.schema.response import SuccessResponse

class ImageHistoryItem(BaseModel):
    history_id: int = Field(..., description="분석 요약 테이블(image_final_detection_results)의 PK")
    image_id: int = Field(..., description="원본 이미지(images)의 PK")
    filename: str = Field(..., description="사용자가 업로드한 원본 파일명")
    file_type: str = Field(..., description="파일 종류 (image 또는 audio)")
    analysis_status: str = Field(..., description="파이프라인 진행 상태")
    is_ai: Optional[bool] = Field(None, description="최종 AI 판별 결과")
    ai_probability: Optional[float] = Field(None, description="AI 확률 (0.0 ~ 1.0)")
    created_at: datetime = Field(..., description="파일 업로드 날짜 및 시간")

    class Config:
        from_attributes = True

class ImageHistoryData(BaseModel):
    total_count: int = Field(..., description="조건에 맞는 전체 데이터 개수")
    total_pages: int = Field(..., description="전체 페이지 수")
    current_page: int = Field(..., description="현재 페이지 번호")
    histories: List[ImageHistoryItem] = Field(..., description="검증 내역 목록")

class ImageHistoryResponse(SuccessResponse):
    data: ImageHistoryData
