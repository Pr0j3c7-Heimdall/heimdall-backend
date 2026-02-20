from app.detection.repository.detection_repository import DetectionRepository
from app.image.repository.image_repository import ImageRepository
from app.detection.exception.detection_exception import AnalysisNotFoundException, ForbiddenAccessException
from app.detection.schema.response.status import DetectionStatusData
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
