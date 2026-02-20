from pydantic import BaseModel, Field
from app.common.schema.response import SuccessResponse

class DetectionStatusData(BaseModel):
    image_id: int = Field(..., description="ID of the image")
    analysis_status: str = Field(..., description="Current status of the analysis pipeline")

class DetectionStatusResponse(SuccessResponse):
    data: DetectionStatusData
