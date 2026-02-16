from fastapi import UploadFile, File
from pydantic import BaseModel

class ImageUploadRequest(BaseModel):
    file: UploadFile = File(...)
