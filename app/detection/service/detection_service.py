from app.detection.repository.detection_repository import DetectionRepository
from app.image.repository.image_repository import ImageRepository
from app.detection.exception.detection_exception import AnalysisNotFoundException, ForbiddenAccessException
from app.detection.schema.response.status import DetectionStatusData
from app.detection.model.image_analysis_summary import AnalysisStatus

class DetectionService:
    def __init__(self, detection_repo: DetectionRepository, image_repo: ImageRepository):
        self.detection_repo = detection_repo
        self.image_repo = image_repo

    async def get_detection_status(self, image_id: int, user_id: int) -> DetectionStatusData:
        # 이미지 조회 (권한 확인을 위해)
        image = await self.image_repo.get_image_by_id(image_id)
        if not image:
             raise AnalysisNotFoundException()
        
        # 권한 확인 (본인이 업로드한 이미지만)
        if image.user_id != user_id:
             raise ForbiddenAccessException()

        # 분석 요약 조회
        summary = await self.detection_repo.get_analysis_summary_by_image_id(image_id)
        if not summary:
             raise AnalysisNotFoundException()
        
        return DetectionStatusData(
             image_id=image_id,
             analysis_status=summary.analysis_status
        )

    async def run_ai_detection(self, image_id: int):
        """
        AI 분석 시뮬레이션: 10초 후 분석 완료(COMPLETED) 상태로 업데이트합니다.
        """
        import asyncio
        from datetime import datetime
        from app.database import AsyncSessionLocal
        from app.detection.repository.detection_repository import DetectionRepository

        print(f"DEBUG: Starting AI detection simulation for image ID: {image_id}")
        await asyncio.sleep(10)

        async with AsyncSessionLocal() as session:
            repo = DetectionRepository(session)
            await repo.update_analysis_status(
                image_id=image_id,
                status=AnalysisStatus.COMPLETED,
                completed_at=datetime.now()
            )
        
        print(f"DEBUG: AI detection simulation COMPLETED for image ID: {image_id}")
