from fastapi import APIRouter, Depends, UploadFile, BackgroundTasks, File

from app.image.dependencies import get_image_service
from app.auth.dependencies import get_current_user_id  # 경로 변경됨
from app.image.service.image_service import ImageService
from app.image.schema.response.upload import ImageUploadResponse, ImageUploadData

router = APIRouter(prefix="/images", tags=["images"])

@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    image_service: ImageService = Depends(get_image_service),
):
    """
    이미지 파일을 업로드하고 AI 검증을 비동기로 시작함.
    """
    uploaded_image = await image_service.upload_image(file, user_id, background_tasks)
    return ImageUploadResponse(
        data=ImageUploadData(
            image_id=uploaded_image.id,
            image_url=uploaded_image.image_url,
            result="업로드 성공 및 AI 검증 시작"
        )
    )