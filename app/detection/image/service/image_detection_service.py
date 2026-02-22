from ..repository.image_detection_repository import DetectionRepository
from ..exception.image_detection_exception import AnalysisNotFoundException, ForbiddenAccessException
from ..schema.response.image_status import DetectionStatusData
from ..schema.response.image_result import (
    DetectionResultData,
    C2PAResultSchema,
    BinaryResultSchema,
    MultiResultSchema
)
from ..model.image_final_detection_results import AnalysisStatus

import asyncio
from datetime import datetime, timezone
import logging
from app.database import AsyncSessionLocal

class DetectionService:
    def __init__(self, detection_repo: DetectionRepository):
        self.detection_repo = detection_repo

    async def get_detection_status(self, image_id: int, user_id: int) -> DetectionStatusData:
        # DetectionRepository의 JOIN 메서드 호출 (순환 참조 방지용)
        status = await self.detection_repo.get_image_status_and_check_owner(image_id, user_id)
        
        if status is None:
            raise AnalysisNotFoundException(message="요청하신 이미지 또는 분석 결과를 찾을 수 없습니다.")
        
        if status == "FORBIDDEN":
            raise ForbiddenAccessException(message="본인이 업로드한 이미지만 조회할 수 있습니다.")
            
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
        if image.c2pa_result:
            c2pa_data = C2PAResultSchema(
                c2pa_id=image.c2pa_result.id,
                is_c2pa_compliant=image.c2pa_result.is_c2pa_compliant,
                created_model=image.c2pa_result.created_model,
                converted_model=image.c2pa_result.converted_model,
                created_description=image.c2pa_result.created_description,
                claim_generator=image.c2pa_result.claim_generator,
                claim_generator_info_name=image.c2pa_result.claim_generator_info_name,
                synth_id=image.c2pa_result.synth_id,
                visible_watermark=image.c2pa_result.visible_watermark,
                total_digital_source_type=image.c2pa_result.total_digital_source_type,
                synth_id_digital_source_type=image.c2pa_result.synth_id_digital_source_type,
                visible_watermark_digital_source_type=image.c2pa_result.visible_watermark_digital_source_type
            )

        binary_results = []
        if image.binary_results:
            binary_results = [
                BinaryResultSchema(
                    binary_id=res.id,
                    detection_method=res.detection_method,
                    confidence_score=res.confidence_score,
                    result_json=res.result_json,
                ) for res in image.binary_results
            ]

        multi_results = []
        if image.multiclass_results:
            multi_results = [
                MultiResultSchema(
                    multi_id=res.id,
                    detection_method=res.detection_method,
                    predicted_model=res.predicted_model,
                    confidence_score=res.confidence_score,
                    result_json=res.result_json,
                ) for res in image.multiclass_results
            ]

        return DetectionResultData(
            image_id=image.id,
            image_url=image.image_url,
            final_is_ai=summary.final_is_ai,
            final_ai_probability=summary.final_ai_probability,
            final_generator_model=summary.final_generator_model,
            completed_at=summary.completed_at,
            c2pa=c2pa_data,
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
