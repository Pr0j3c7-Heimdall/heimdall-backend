from app.detection.repository.detection_repository import DetectionRepository
from app.image.repository.image_repository import ImageRepository
from app.detection.exception.detection_exception import AnalysisNotFoundException, ForbiddenAccessException
from app.detection.schema.response.status import DetectionStatusData
from app.detection.schema.response.result import DetectionResultData, C2PAResultSchema, BinaryResultSchema, MultiResultSchema
from app.detection.model.image_analysis_summary import AnalysisStatus

import asyncio
from datetime import datetime, timezone
import logging
from app.database import AsyncSessionLocal
from app.detection.repository.detection_repository import DetectionRepository

class DetectionService:
    def __init__(self, detection_repo: DetectionRepository, image_repo: ImageRepository):
        self.detection_repo = detection_repo
        self.image_repo = image_repo

    async def get_detection_status(self, image_id: int, user_id: int) -> DetectionStatusData:
        # Repository의 JOIN 메서드 단 한 번 호출 (권한 체크 및 상태 조회 동시 수행)
        status = await self.image_repo.get_image_status_and_check_owner(image_id, user_id)
        
        return DetectionStatusData(
            image_id=image_id,
            analysis_status=status
        )

    async def get_detection_result(self, image_id: int, user_id: int) -> DetectionResultData:
        """이미지 ID를 기준으로 모든 분석 결과(C2PA, 이진, 다중 분류)를 포함하여 조회함"""
        image = await self.detection_repo.get_full_detection_result(image_id)
        
        if not image:
            raise AnalysisNotFoundException(message="요청하신 이미지 또는 분석 결과를 찾을 수 없습니다.")
        
        if image.user_id != user_id:
            raise ForbiddenAccessException(message="본인이 업로드한 이미지만 조회할 수 있습니다.")
            
        summary = image.analysis_summary
        if not summary or summary.analysis_status != AnalysisStatus.COMPLETED:
            raise AnalysisNotFoundException(message="분석이 완료되지 않았거나 이미지를 찾을 수 없습니다.")

        c2pa_data = None
        if hasattr(image, "c2pa_result") and image.c2pa_result:
            c2pa_data = C2PAResultSchema(
                C2PA_id=image.c2pa_result.id,
                is_c2pa_compliant=image.c2pa_result.is_c2pa_compliant,
                signature_status=image.c2pa_result.signature_status,
                generator_model=image.c2pa_result.generator_model,
                require_ai_inference=image.c2pa_result.requires_ai_inference
            )

        binary_results = []
        if hasattr(image, "binary_results") and image.binary_results:
            binary_results = [
                BinaryResultSchema(
                    binary_id=res.id,
                    detection_method=res.detection_method,
                    is_detected=res.is_detected,
                    confidence_score=res.confidence_score
                ) for res in image.binary_results
            ]

        multi_results = []
        if hasattr(image, "multiclass_results") and image.multiclass_results:
            multi_results = [
                MultiResultSchema(
                    multi_id=res.id,
                    detection_method=res.detection_method,
                    predicted_model=res.predicted_model,
                    confidence_score=res.confidence_score
                ) for res in image.multiclass_results
            ]

        return DetectionResultData(
            image_id=image.id,
            image_url=image.image_url,
            final_is_ai=summary.final_is_ai,
            final_ai_probability=summary.final_ai_probability,
            final_generator_model=summary.final_generator_model,
            completed_at=summary.completed_at,
            C2PA=c2pa_data,
            binary=binary_results,
            multi=multi_results
        )

    async def run_ai_detection(self, image_id: int):
        """
        AI 분석 시뮬레이션: 10초 후 분석 완료(COMPLETED) 상태로 업데이트합니다.
        """

        logging.info(f"DEBUG: Starting AI detection simulation for image ID: {image_id}")
        await asyncio.sleep(10)

        async with AsyncSessionLocal() as session:
            repo = DetectionRepository(session)
            await repo.update_analysis_status(
                image_id=image_id,
                status=AnalysisStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc)
            )
        
        logging.info(f"DEBUG: AI detection simulation COMPLETED for image ID: {image_id}")
