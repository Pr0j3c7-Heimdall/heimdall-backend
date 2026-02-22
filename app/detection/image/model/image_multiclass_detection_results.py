from sqlalchemy import Column, BigInteger, String, Float, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class ImageMulticlassDetectionResult(Base):
    __tablename__ = "image_multiclass_detection_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    image_id = Column(BigInteger, ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    detection_method = Column(String(50), nullable=False)
    predicted_model = Column(String(100))
    confidence_score = Column(Float)
    result_json = Column(JSON)

    image = relationship("Image", backref="multiclass_results")