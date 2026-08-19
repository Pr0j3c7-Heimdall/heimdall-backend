from fastapi import APIRouter

from app.audio.router import router as audio_router

base_router = APIRouter()
base_router.include_router(audio_router)
