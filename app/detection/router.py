from fastapi import APIRouter
from app.detection.image.router import router as image_router
from app.detection.audio.router import router as audio_router


router = APIRouter(prefix="/detection")

router.include_router(image_router)
router.include_router(audio_router)
