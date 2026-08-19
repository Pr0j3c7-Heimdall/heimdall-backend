from fastapi import UploadFile, File
from pydantic import BaseModel

class AudioUploadRequest(BaseModel):
    file: UploadFile = File(...)
