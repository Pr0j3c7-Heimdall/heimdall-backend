from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Image(Base):
    __tablename__ = "images"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    image_url = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # User 모델이 존재하며 'images' 관계가 설정되어 있다고 가정함.
    # 해당 관계는 User 모델에도 정의되어야 함.
    # 예시 (app/auth/model/user.py):
    # images = relationship("Image", back_populates="owner")
    owner = relationship("User", back_populates="images")
    analysis_summary = relationship("ImageAnalysisSummary", back_populates="image", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Image(id={self.id}, filename='{self.filename}', image_url='{self.image_url}')>"