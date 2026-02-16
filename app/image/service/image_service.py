from typing import List
from fastapi import UploadFile, BackgroundTasks

from app.image.repository.image_repository import ImageRepository
from app.image.model.image import Image
from app.image.exception.image_exception import InvalidImageFileException


class ImageService:
    def __init__(self, image_repository: ImageRepository):
        self.image_repository = image_repository

    async def upload_image(self, file: UploadFile, user_id: int, background_tasks: BackgroundTasks) -> Image:
        # 1. 파일 형식 검증
        allowed_mime_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_mime_types:
            raise InvalidImageFileException(message="지원하지 않는 이미지 파일 형식입니다.")

        # 2. 레포지토리를 통한 파일 및 메타데이터 저장
        new_image = await self.image_repository.save_image_file(file, user_id)

        # 3. 비동기 AI 검증 작업 호출
        background_tasks.add_task(self._run_ai_validation, new_image.id)

        return new_image

    async def _run_ai_validation(self, image_id: int):
        """
        AI 검증 로직을 위한 임시 함수.
        일반적으로 외부 AI 서비스를 호출한 뒤, 그 결과를 데이터베이스의 Image 레코드에 업데이트함.
        """
        print(f"Running AI validation for image ID: {image_id}")
        
        # 예시: AI 처리 과정 시뮬레이션
        import asyncio
        await asyncio.sleep(5)  # 지연 시간 시뮬레이션
        print(f"AI validation completed for image ID: {image_id}")
        
        # 실제 환경에서는 DB의 이미지 상태/결과를 업데이트해야 함.