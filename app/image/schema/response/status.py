from pydantic import BaseModel

class ImageStatusData(BaseModel):
    image_id: int
    analysis_status: str

class ImageStatusResponse(BaseModel):
    success: bool = True
    data: ImageStatusData