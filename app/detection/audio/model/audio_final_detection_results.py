from enum import Enum
from sqlalchemy import Column, BigInteger, String, Boolean, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class AudioAnalysisStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"

class AudioFinalDetectionResult(Base):
    __tablename__ = "audio_final_detection_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    audio_id = Column(BigInteger, ForeignKey("audios.id", ondelete="CASCADE"), nullable=False, unique=True)
    analysis_status = Column(String(50), default=AudioAnalysisStatus.PENDING)
    final_is_ai = Column(Boolean)
    final_ai_probability = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    audio = relationship("Audio", back_populates="analysis_summary")

    def __repr__(self):
        return f"<AudioFinalDetectionResult(audio_id={self.audio_id}, status='{self.analysis_status}')>"
