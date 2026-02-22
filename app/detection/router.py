from fastapi import APIRouter
from app.detection.image.router import router as image_router


router = APIRouter(prefix="/detection")

router.include_router(image_router)
# 나중에 audio 탐지 라우터가 생기면 주석 삭제
# router.include_router(audio_router)
