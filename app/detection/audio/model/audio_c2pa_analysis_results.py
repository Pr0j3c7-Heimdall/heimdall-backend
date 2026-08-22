from sqlalchemy import Column, BigInteger, String, Boolean, ForeignKey
from sqlalchemy.orm import backref, relationship
from app.database import Base


class AudioC2paAnalysisResult(Base):
    """오디오 C2PA 분석 결과.

    컬럼 구성은 image_c2pa_analysis_results와 거의 동일하다. C2PA 매니페스트 구조가
    포맷과 무관하고, 프론트엔드가 이미지/오디오 응답을 같은 코드로 다룰 수 있어야
    하기 때문이다.

    다만 visible_watermark 계열 2개는 두지 않는다. 오디오에 "보이는" 워터마크는
    성립하지 않아 구조적으로 항상 NULL이 되기 때문이다.
    반면 synth_id 계열은 유지한다. SynthID는 오디오 워터마킹을 지원하며,
    speech 트랙의 주요 생성 도구(ElevenLabs)가 C2PA와 함께 삽입하고 있다.
    """

    __tablename__ = "audio_c2pa_analysis_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    audio_id = Column(BigInteger, ForeignKey("audios.id", ondelete="CASCADE"), nullable=False, unique=True)
    is_c2pa_compliant = Column(Boolean, nullable=False)

    created_model = Column(String(255))
    converted_model = Column(String(255))
    created_description = Column(String(255))
    claim_generator = Column(String(255))
    claim_generator_info_name = Column(String(255))
    synth_id = Column(String(255))
    total_digital_source_type = Column(String(255))
    synth_id_digital_source_type = Column(String(255))

    # audio_id가 unique이므로 역참조도 스칼라로 둔다.
    audio = relationship("Audio", backref=backref("c2pa_result", uselist=False))

    def __repr__(self):
        return f"<AudioC2paAnalysisResult(audio_id={self.audio_id}, compliant={self.is_c2pa_compliant})>"
