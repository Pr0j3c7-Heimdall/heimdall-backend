from sqlalchemy import Column, BigInteger, String, Boolean, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class C2paVerificationResult(Base):
    __tablename__ = "c2pa_verification_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    image_id = Column(BigInteger, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, unique=True)
    is_c2pa_compliant = Column(Boolean, nullable=False)
    signature_status = Column(String(100))
    generator_model = Column(String(100))
    requires_ai_inference = Column(Boolean, default=True)
    provenance_data_json = Column(JSON)
    analysis_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # 1:1 관계 설정
    image = relationship("Image", backref="c2pa_result", uselist=False)