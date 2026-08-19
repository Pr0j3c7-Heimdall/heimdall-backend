from sqlalchemy import Column, BigInteger, String, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class AudioModelDetectionResult(Base):
    __tablename__ = "audio_model_detection_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    audio_id = Column(BigInteger, ForeignKey("audios.id", ondelete="CASCADE"), nullable=False)
    # 모델명: SSL-AASIST / RawNet3 / CQCC-SSL-AASIST (speech), AASIST / RawNet3 / LCNN (singing)
    detection_method = Column(String(50), nullable=False)
    confidence_score = Column(Float)
    result_json = Column(JSON)

    audio = relationship("Audio", backref="model_results")
