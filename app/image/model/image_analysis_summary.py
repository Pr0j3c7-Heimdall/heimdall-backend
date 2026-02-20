from sqlalchemy import Column, BigInteger, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class ImageAnalysisSummary(Base):
    __tablename__ = "image_analysis_summary"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    image_id = Column(BigInteger, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, unique=True)
    analysis_status = Column(String(50), default="PENDING")
    final_is_ai = Column(Boolean, nullable=True)
    final_ai_probability = Column(Float, nullable=True)
    requires_multiclass = Column(Boolean, default=False)
    final_generator_model = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    image = relationship("Image", back_populates="analysis_summary")

    def __repr__(self):
        return f"<ImageAnalysisSummary(image_id={self.image_id}, status='{self.analysis_status}')>"
