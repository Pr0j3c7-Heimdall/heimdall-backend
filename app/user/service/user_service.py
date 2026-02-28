from __future__ import annotations

import math
from typing import Optional
from app.user.repository import UserRepository
from app.user.schema.response.history import ImageHistoryData, ImageHistoryItem


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def get_image_history(
        self,
        user_id: int,
        page: int = 1,
        size: int = 10,
        keyword: Optional[str] = None,
        result_type: Optional[str] = None
    ) -> ImageHistoryData:
        """사용자의 이미지 검증 내역을 조회함"""
        total_count, rows = await self.user_repository.get_image_detection_history(
            user_id=user_id,
            page=page,
            size=size,
            keyword=keyword,
            result_type=result_type
        )

        total_pages = math.ceil(total_count / size) if total_count > 0 else 0

        histories = []
        for image, summary in rows:
            histories.append(
                ImageHistoryItem(
                    history_id=summary.id,
                    image_id=image.id,
                    filename=image.filename,
                    file_type="image",
                    analysis_status=summary.analysis_status,
                    is_ai=summary.final_is_ai,
                    ai_probability=summary.final_ai_probability,
                    created_at=image.created_at
                )
            )

        return ImageHistoryData(
            total_count=total_count,
            total_pages=total_pages,
            current_page=page,
            histories=histories
        )
