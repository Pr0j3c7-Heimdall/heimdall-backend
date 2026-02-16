from typing import List
from fastapi import UploadFile, BackgroundTasks

from app.image.repository.image_repository import ImageRepository
from app.image.model.image import Image
from app.image.exception.image_exception import InvalidImageFileException

# 모듈 레벨 상수로 분리
ALLOWED_MIME_TYPES = frozenset(["image/jpeg", "image/png", "image/webp"])

class ImageService:
    def __init__(self, image_repository: ImageRepository):
        self.image_repository = image_repository

    async def upload_image(self, file: UploadFile, user_id: int, background_tasks: BackgroundTasks) -> Image:
        # 1. 파일 형식 검증
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise InvalidImageFileException(message="지원하지 않는 이미지 파일 형식입니다.")

        # 2. 레포지토리를 통한 파일 및 메타데이터 저장
        new_image = await self.image_repository.save_image_file(file, user_id)

        # 3. 비동기 AI 검증 작업 호출
        background_tasks.add_task(self._run_ai_validation, new_image.id)

        return new_image

    async def _run_ai_validation(self, image_id: int):
        print(f"Running AI validation for image ID: {image_id}")
        import asyncio
        await asyncio.sleep(5)
        print(f"AI validation completed for image ID: {image_id}")