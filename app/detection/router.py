from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user_id
from app.detection.dependencies import get_detection_service
from app.detection.service.detection_service import DetectionService
from app.detection.schema.response.status import DetectionStatusResponse
from app.detection.schema.response.result import DetectionResultResponse

router = APIRouter(prefix="/detection", tags=["detection"])

@router.get("/{image_id}/status", response_model=DetectionStatusResponse)
async def get_detection_status(
    image_id: int,
    user_id: int = Depends(get_current_user_id),
    detection_service: DetectionService = Depends(get_detection_service)
):
    """AI 검증 파이프라인의 현재 상태 및 최종 결과를 조회함."""
    status_data = await detection_service.get_detection_status(image_id, user_id)
    return DetectionStatusResponse(data=status_data)

@router.get("/{image_id}/result", response_model=DetectionResultResponse)
async def get_detection_result(
    image_id: int,
    user_id: int = Depends(get_current_user_id),
    detection_service: DetectionService = Depends(get_detection_service)
):
    """AI 검증 파이프라인 분석이 완료된 후 상세 결과를 조회함."""
    result_data = await detection_service.get_detection_result(image_id, user_id)
    return DetectionResultResponse(data=result_data)
