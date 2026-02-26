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
from app.ai_pipeline.image.image_pipeline import execute_image_pipeline

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
        # backref로 생성된 c2pa_result가 리스트로 반환될 수 있으므로 안전하게 처리
        c2pa_obj = image.c2pa_result[0] if isinstance(image.c2pa_result, list) and len(image.c2pa_result) > 0 else image.c2pa_result
        
        if c2pa_obj and not isinstance(c2pa_obj, list):
            c2pa_data = C2PAResultSchema(
                c2pa_id=c2pa_obj.id,
                is_c2pa_compliant=c2pa_obj.is_c2pa_compliant,
                created_model=c2pa_obj.created_model,
                converted_model=c2pa_obj.converted_model,
                created_description=c2pa_obj.created_description,
                claim_generator=c2pa_obj.claim_generator,
                claim_generator_info_name=c2pa_obj.claim_generator_info_name,
                synth_id=c2pa_obj.synth_id,
                visible_watermark=c2pa_obj.visible_watermark,
                total_digital_source_type=c2pa_obj.total_digital_source_type,
                synth_id_digital_source_type=c2pa_obj.synth_id_digital_source_type,
                visible_watermark_digital_source_type=c2pa_obj.visible_watermark_digital_source_type
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

    async def run_ai_detection(self, image_id: int, image_path: str):
        """
        AI 분석 파이프라인을 실행하고 결과를 단계별로 DB에 업데이트합니다.
        """
        logging.info(f"DEBUG: Starting AI detection for image ID: {image_id}")

        async def update_progress(status: str, data: dict = None):
            """클로저를 통해 단계별 상태 및 결과를 DB에 반영"""
            async with AsyncSessionLocal() as session:
                repo = DetectionRepository(session)
                # 1. 상태 업데이트
                await repo.update_analysis_status(image_id=image_id, status=status)
                
                # 2. 결과가 있다면 저장
                if data:
                    if "c2pa" in data:
                        await repo.save_c2pa_result(image_id=image_id, data=data["c2pa"])
                    if "binary" in data:
                        await repo.save_binary_result(image_id=image_id, data_list=data["binary"])
                    if "multi" in data:
                        await repo.save_multiclass_result(image_id=image_id, data_list=data["multi"])

        # 파이프라인 실행
        pipeline_output = await execute_image_pipeline(
            image_path=image_path, 
            progress_callback=update_progress
        )

        # 최종 상태 및 결과 요약 업데이트
        final_res = pipeline_output["final_result"]
        async with AsyncSessionLocal() as session:
            repo = DetectionRepository(session)
            await repo.update_analysis_status(
                image_id=image_id,
                status=AnalysisStatus.COMPLETED,
                final_is_ai=final_res["final_is_ai"],
                final_ai_probability=final_res["final_ai_probability"],
                requires_multiclass=final_res["requires_multiclass"],
                completed_at=datetime.now(timezone.utc)
            )
        
        logging.info(f"DEBUG: AI detection COMPLETED for image ID: {image_id}")
