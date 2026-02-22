from sqlalchemy import Column, BigInteger, String, Boolean, Float, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class ImageBinaryDetectionResult(Base):
    __tablename__ = "image_binary_detection_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    image_id = Column(BigInteger, ForeignKey("images.id"), nullable=False)
    detection_method = Column(String(50), nullable=False)
    confidence_score = Column(Float)
    result_json = Column(JSON)
    analysis_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # image 테이블과의 관계 (필요 시 양방향 참조를 위해 설정)
    image = relationship("Image", backref="binary_results")