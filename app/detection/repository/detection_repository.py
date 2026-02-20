from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import update
from app.detection.model.image_analysis_summary import ImageAnalysisSummary, AnalysisStatus

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

    async def update_analysis_status(self, image_id: int, status: AnalysisStatus, **kwargs) -> None:
        """이미지 분석 상태 및 추가 필드(결과 등)를 업데이트함"""
        stmt = (
            update(ImageAnalysisSummary)
            .where(ImageAnalysisSummary.image_id == image_id)
            .values(analysis_status=status, **kwargs)
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()
