from fastapi import UploadFile, BackgroundTasks

from app.image.repository.image_repository import ImageRepository
from app.detection.image.repository.image_detection_repository import DetectionRepository
from app.detection.image.service.image_detection_service import DetectionService
from app.image.model.image import Image
from app.image.exception.image_exception import InvalidImageFileException

import magic

# 모듈 레벨 상수로 분리
ALLOWED_MIME_TYPES = frozenset(["image/jpeg", "image/png", "image/webp"])

class ImageService:
    def __init__(self, image_repository: ImageRepository, detection_repository: DetectionRepository, detection_service: DetectionService):
        self.image_repository = image_repository
        self.detection_repository = detection_repository
        self.detection_service = detection_service

    async def upload_image(self, file: UploadFile, user_id: int, background_tasks: BackgroundTasks) -> Image:
        # 파일의 실제 데이터(바이트)를 조금 읽어서 MIME 타입 확인
        file_header = await file.read(32) 
        actual_mime_type = magic.from_buffer(file_header, mime=True)
        
        # 제대로 저장하기 위해 파일의 처음으로 포인터를 되돌려 놓기
        await file.seek(0) 

        # 클라이언트가 보낸 헤더가 아니라, 실제 파악한 MIME 타입으로 검증
        if actual_mime_type not in ALLOWED_MIME_TYPES:
            raise InvalidImageFileException(message="지원하지 않거나 변조된 이미지 파일 형식입니다.")
        
        new_image = await self.image_repository.save_image_file(file, user_id)
        
        # 검증 도메인에 분석 시작을 위임
        background_tasks.add_task(self.detection_service.run_ai_detection, new_image.id)
        
        return new_image