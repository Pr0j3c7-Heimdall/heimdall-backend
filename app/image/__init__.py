from fastapi import APIRouter

from app.image.router import router as image_router

base_router = APIRouter()
base_router.include_router(image_router)
