from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import selectinload
from typing import Optional

# 순환 참조 방지를 위해 상대 경로 또는 직접 경로 사용
from ..model.image_final_detection_results import ImageFinalDetectionResult, AnalysisStatus
from ..model.image_c2pa_analysis_results import ImageC2paAnalysisResult
from ..model.image_binary_detection_results import ImageBinaryDetectionResult
from ..model.image_multiclass_detection_results import ImageMulticlassDetectionResult
from app.image.model.image import Image

class DetectionRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_analysis_summary(self, image_id: int) -> ImageFinalDetectionResult:
        """새로운 분석 요약 레코드를 생성함 (PENDING 상태)"""
        summary = ImageFinalDetectionResult(image_id=image_id, analysis_status=AnalysisStatus.PENDING)
        self.db_session.add(summary)
        await self.db_session.flush()
        await self.db_session.commit()
        return summary

    async def get_analysis_summary_by_image_id(self, image_id: int) -> ImageFinalDetectionResult:
        """이미지 ID를 기준으로 분석 요약 레코드를 조회함"""
        stmt = select(ImageFinalDetectionResult).where(ImageFinalDetectionResult.image_id == image_id)
        result = await self.db_session.execute(stmt)
        return result.scalars().first()

    async def get_full_detection_result(self, image_id: int) -> Optional[Image]:
        """이미지 ID를 기준으로 이미지 정보와 모든 분석 결과를 포함하여 조회함"""
        stmt = (
            select(Image)
            .where(Image.id == image_id)
            .options(
                selectinload(Image.analysis_summary),
                selectinload(Image.c2pa_result),
                selectinload(Image.binary_results),
                selectinload(Image.multiclass_results)
            )
        )
        result = await self.db_session.execute(stmt)
        return result.scalars().first()

    async def update_analysis_status(self, image_id: int, status: AnalysisStatus, **kwargs) -> None:
        """이미지 분석 상태 및 추가 필드(결과 등)를 업데이트함"""
        stmt = (
            update(ImageFinalDetectionResult)
            .where(ImageFinalDetectionResult.image_id == image_id)
            .values(analysis_status=status, **kwargs)
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()

    async def get_image_status_and_check_owner(self, image_id: int, user_id: int) -> str:
        """
        이미지 소유권을 확인하고 현재 분석 상태를 한 번에 조회함.
        (순환 참조 방지를 위해 DetectionRepository에서 직접 수행)
        """
        stmt = (
            select(Image, ImageFinalDetectionResult.analysis_status)
            .join(ImageFinalDetectionResult, Image.id == ImageFinalDetectionResult.image_id)
            .where(Image.id == image_id)
        )
        result = await self.db_session.execute(stmt)
        row = result.first()
        
        if not row:
            # 예외 처리는 Service에서 수행할 수 있도록 None 또는 결과 반환
            return None
            
        image, status = row
        
        # 소유자 확인
        if image.user_id != user_id:
            # Service에서 ForbiddenAccessException을 던질 수 있도록 특수한 값 반환 또는 여기서 직접 처리
            return "FORBIDDEN"
            
        return status

    async def save_c2pa_result(self, image_id: int, data: dict) -> None:
        """C2PA 분석 결과를 저장함"""
        c2pa_result = ImageC2paAnalysisResult(
            image_id=image_id,
            is_c2pa_compliant=data.get("is_c2pa_compliant"),
            created_model=data.get("created_model"),
            converted_model=data.get("converted_model"),
            created_description=data.get("created_description"),
            claim_generator=data.get("claim_generator"),
            claim_generator_info_name=data.get("claim_generator_info_name"),
            synth_id=data.get("synth_id"),
            visible_watermark=data.get("visible_watermark"),
            total_digital_source_type=data.get("total_digital_source_type"),
            synth_id_digital_source_type=data.get("synth_id_digital_source_type"),
            visible_watermark_digital_source_type=data.get("visible_watermark_digital_source_type")
        )
        self.db_session.add(c2pa_result)
        await self.db_session.commit()

    async def save_binary_result(self, image_id: int, data_list: list) -> None:
        """이진 분류 결과들을 리스트 단위로 저장함"""
        for data in data_list:
            binary_result = ImageBinaryDetectionResult(
                image_id=image_id,
                detection_method=data.get("detection_method"),
                confidence_score=data.get("confidence_score"),
                result_json=data.get("result_json")
            )
            self.db_session.add(binary_result)
        await self.db_session.commit()

    async def save_multiclass_result(self, image_id: int, data_list: list) -> None:
        """다중 분류 결과들을 리스트 단위로 저장함"""
        for data in data_list:
            multiclass_result = ImageMulticlassDetectionResult(
                image_id=image_id,
                detection_method=data.get("detection_method"),
                predicted_model=data.get("predicted_model"),
                confidence_score=data.get("confidence_score"),
                result_json=data.get("result_json")
            )
            self.db_session.add(multiclass_result)
        await self.db_session.commit()