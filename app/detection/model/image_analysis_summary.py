from enum import Enum
from sqlalchemy import Column, BigInteger, String, Boolean, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class AnalysisStatus(str, Enum):
    PENDING = "PENDING"
    C2PA_PROCESSING = "C2PA_PROCESSING"
    BINARY_PROCESSING = "BINARY_PROCESSING"
    MULTICLASS_PROCESSING = "MULTICLASS_PROCESSING"
    COMPLETED = "COMPLETED"

class ImageAnalysisSummary(Base):
    __tablename__ = "image_analysis_summary"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    image_id = Column(BigInteger, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, unique=True)
    analysis_status = Column(String(50), default=AnalysisStatus.PENDING)
    final_is_ai = Column(Boolean)
    final_ai_probability = Column(Float)
    requires_multiclass = Column(Boolean, default=False)
    final_generator_model = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    image = relationship("Image", backref="analysis_summary", uselist=False)

    def __repr__(self):
        return f"<ImageAnalysisSummary(image_id={self.image_id}, status='{self.analysis_status}')>"
