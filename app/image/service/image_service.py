from typing import List
from fastapi import UploadFile, BackgroundTasks

from app.image.repository.image_repository import ImageRepository
from app.image.model.image import Image
from app.image.exception.image_exception import InvalidImageFileException
from app.database import AsyncSessionLocal

import magic
import asyncio

# 모듈 레벨 상수로 분리
ALLOWED_MIME_TYPES = frozenset(["image/jpeg", "image/png", "image/webp"])

class ImageService:
    def __init__(self, image_repository: ImageRepository):
        self.image_repository = image_repository

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
        
        background_tasks.add_task(self._run_ai_validation, new_image.id)
        
        return new_image

    async def _run_ai_validation(self, image_id: int):
        """
        [임시 모킹 함수] 클라이언트(프론트엔드)의 상태 조회 API(Polling) 연동 테스트를 위한 가짜 로직입니다.
        TODO: 나중에 이 부분을 지우고 실제 DINOv3, ConvNeXt v2, HGBT 등의 AI 모델 추론 파이프라인으로 대체해야 합니다.
        """

        print(f"Running AI validation for image ID: {image_id}")
        await asyncio.sleep(60)
        

        try:
            # 기존 세션과 충돌하지 않도록 async with로 새 세션을 열고 닫습니다.
            async with AsyncSessionLocal() as bg_session:
                bg_repository = ImageRepository(bg_session)
                await bg_repository.update_image_status(image_id, "COMPLETED")
                
            print(f"AI validation completed for image ID: {image_id}")
            
        except Exception as e:
            print(f"[{image_id}] 백그라운드 작업 중 에러 발생: {e}")

    async def get_image_status(self, image_id: int, user_id: int) -> str:
            """
            특정 이미지의 분석 상태를 조회함.
            """
            return await self.image_repository.get_image_status_and_check_owner(image_id, user_id)