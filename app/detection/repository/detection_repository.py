from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import selectinload
from typing import Optional
from app.detection.model.image_analysis_summary import ImageAnalysisSummary, AnalysisStatus
from app.detection.model.c2pa_verification_result import C2paVerificationResult
from app.detection.model.binary_detection_result import BinaryDetectionResult
from app.detection.model.multiclass_detection_result import MulticlassDetectionResult
from app.image.model.image import Image

class DetectionRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_analysis_summary(self, image_id: int) -> ImageAnalysisSummary:
        """새로운 분석 요약 레코드를 생성함 (PENDING 상태)"""
        summary = ImageAnalysisSummary(image_id=image_id, analysis_status=AnalysisStatus.PENDING)
        self.db_session.add(summary)
        await self.db_session.flush()
        await self.db_session.commit()
        return summary

    async def get_analysis_summary_by_image_id(self, image_id: int) -> ImageAnalysisSummary:
        """이미지 ID를 기준으로 분석 요약 레코드를 조회함"""
        stmt = select(ImageAnalysisSummary).where(ImageAnalysisSummary.image_id == image_id)
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
            update(ImageAnalysisSummary)
            .where(ImageAnalysisSummary.image_id == image_id)
            .values(analysis_status=status, **kwargs)
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()
