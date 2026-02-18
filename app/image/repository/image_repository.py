import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import UploadFile

from app.image.model.image import Image
from app.config import get_image_settings
from app.image.exception.image_exception import ImageNotFoundException

settings = get_image_settings()

class ImageRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        # settings에 설정된 업로드 기본 디렉토리 정의
        self.upload_base_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_base_dir, exist_ok=True)

    async def save_image_file(self, file: UploadFile, user_id: int) -> Image:
        """
        이미지 파일을 로컬 파일 시스템에 저장하고 데이터베이스에 Image 레코드를 생성함.
        """
        # 충돌 방지를 위한 고유 파일명 생성
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # 파일 관리를 위한 사용자별 하위 디렉토리 생성
        user_upload_dir = os.path.join(self.upload_base_dir, str(user_id))
        os.makedirs(user_upload_dir, exist_ok=True)

        file_path = os.path.join(user_upload_dir, unique_filename)

        # 파일 저장
        with open(file_path, "wb") as buffer:
            while content := await file.read(1024):  # 청크 단위로 읽기
                buffer.write(content)

        # image_url이 정적 경로 또는 CDN을 통해 제공된다고 가정함.
        # 배포 환경에 따라 수정이 필요할 수 있으며, 현재는 기본 URL을 바탕으로 구성함.
        image_url = f"{settings.BASE_URL}/uploads/{user_id}/{unique_filename}"

        # 데이터베이스에 이미지 메타데이터 생성 및 저장
        # DB가 타임스탬프를 자동 관리하도록 created_at, updated_at 제거
        new_image = Image(
            user_id=user_id,
            filename=file.filename,
            filepath=file_path,
            image_url=image_url
        )
        self.db_session.add(new_image)
        await self.db_session.flush()
        
        await self.db_session.commit()
        await self.db_session.refresh(new_image)
        return new_image
    
    async def get_image_by_id(self, image_id: int) -> Image:
        """
        데이터베이스에서 ID를 기준으로 이미지 레코드를 조회함.
        """
        stmt = select(Image).where(Image.id == image_id)
        result = await self.db_session.execute(stmt)
        image = result.scalars().first()
        if not image:
            raise ImageNotFoundException()
        return image