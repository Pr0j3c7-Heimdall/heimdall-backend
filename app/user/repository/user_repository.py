from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.user.model import User, UserStatus
from app.image.model.image import Image
from app.detection.image.model.image_final_detection_results import ImageFinalDetectionResult


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_provider_sub(self, provider: str, provider_sub: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.provider == provider,
                User.provider_sub == provider_sub,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, email: str, name: str, provider: str, provider_sub: str) -> User:
        user = User(
            email=email,
            name=name,
            provider=provider,
            provider_sub=provider_sub,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def find_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def withdraw(self, user_id: int) -> None:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(status=UserStatus.DELETED, deleted_at=now)
        )

    async def restore(self, user_id: int) -> None:
        """탈퇴한 계정 복구 (재가입)"""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(status=UserStatus.ACTIVE, deleted_at=None)
        )

    async def get_image_detection_history(
        self,
        user_id: int,
        page: int = 1,
        size: int = 10,
        keyword: Optional[str] = None,
        result_type: Optional[str] = None
    ) -> Tuple[int, List[Tuple[Image, ImageFinalDetectionResult]]]:
        """
        사용자의 이미지 검증 내역을 조회함 (필터링, 정렬, 페이징 포함)
        """
        # 기본 쿼리
        base_stmt = (
            select(Image, ImageFinalDetectionResult)
            .join(ImageFinalDetectionResult, Image.id == ImageFinalDetectionResult.image_id)
            .where(Image.user_id == user_id)
        )

        # 필터링: keyword
        if keyword:
            base_stmt = base_stmt.where(Image.filename.ilike(f"%{keyword}%"))

        # 필터링: result_type
        if result_type == "ai":
            base_stmt = base_stmt.where(ImageFinalDetectionResult.final_is_ai) 
        elif result_type == "real":
            base_stmt = base_stmt.where(ImageFinalDetectionResult.final_is_ai.is_(False))

        # 전체 개수 계산 (count용 쿼리)
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_count = await self.db.execute(count_stmt)
        total_count = total_count.scalar()

        # 정렬 및 페이징
        stmt = (
            base_stmt.order_by(Image.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return total_count, rows
