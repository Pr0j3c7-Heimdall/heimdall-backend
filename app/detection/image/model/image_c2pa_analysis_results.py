from sqlalchemy import Column, BigInteger, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class ImageC2paAnalysisResult(Base):
    __tablename__ = "image_c2pa_analysis_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    image_id = Column(BigInteger, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, unique=True)
    is_c2pa_compliant = Column(Boolean, nullable=False)
    
    created_model = Column(String(255))
    converted_model = Column(String(255))
    created_description = Column(String(255))
    claim_generator = Column(String(255))
    claim_generator_info_name = Column(String(255))
    synth_id = Column(String(255))
    visible_watermark = Column(String(255))
    total_digital_source_type = Column(String(255))
    synth_id_digital_source_type = Column(String(255))
    visible_watermark_digital_source_type = Column(String(255))

    image = relationship("Image", backref="c2pa_result", uselist=False)