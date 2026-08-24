from enum import Enum

from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AudioTrack(str, Enum):
    SPEECH = "speech"
    SINGING = "singing"


class Audio(Base):
    __tablename__ = "audios"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    audio_url = Column(String(500), nullable=False)
    # 업로드 직후에는 NULL. C2PA 통과로 모델 판별을 건너뛰거나(C2PA 준수) YAMNet이 예외로
    # 판정한 파일(UNSUPPORTED)은 끝까지 NULL로 남는다 — YAMNet Type 판별을 통과한 경우에만 채워짐
    track = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="audios")
    analysis_summary = relationship("AudioFinalDetectionResult", back_populates="audio", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Audio(id={self.id}, filename='{self.filename}', track='{self.track}')>"
