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
    # 음성/가창 라우팅이 자동화되지 않아(YAMNet 임계값 미확정) 업로드 시 클라이언트가 지정함
    track = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="audios")
    analysis_summary = relationship("AudioFinalDetectionResult", back_populates="audio", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Audio(id={self.id}, filename='{self.filename}', track='{self.track}')>"
