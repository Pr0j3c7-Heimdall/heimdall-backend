"""
LFCC-LCNN 단건 추론 모듈. 가창 트랙 전용.

heimdall-vox의 score_test.py가 그렇듯, forward()가 아니라 _compute_embedding() +
_compute_score(inference=True)를 직접 호출한다 (raw_score는 sigmoid 이전 값 -- 다른
네 모델의 score_test.py와 스케일을 맞추기 위해 이 프로젝트 컨벤션으로 그렇게 되어 있음,
LCNN_inference.py 상단 주석 및 heimdall-vox score_test.py 참고).
"""
import torch

from app.ai_pipeline.audio.common.audio_preprocessing import load_waveform
from .LCNN_model import Model


class _PrjConf:
    """Model.__init__(prj_conf=...) 시그니처 호환용 최소 shim. LCNN_model.Model은
    protocol_parse()를 쓰지 않도록 축소했으므로 실제로는 사용되지 않는다."""
    optional_argument = [""]


class LcnnDetector:
    """LFCC-LCNN 단건 추론기."""

    def __init__(self, weight_path: str, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Model(in_dim=1, out_dim=1, args=None, prj_conf=_PrjConf()).to(self.device)
        self.model.load_state_dict(torch.load(weight_path, map_location=self.device))
        self.model.eval()

    @torch.no_grad()
    def predict(self, audio_path: str) -> float:
        """raw_score(sigmoid 이전 값) 반환."""
        waveform = load_waveform(audio_path)
        x = torch.from_numpy(waveform).unsqueeze(0).unsqueeze(-1).to(self.device)
        feature_vec = self.model._compute_embedding(x, None)
        score = self.model._compute_score(feature_vec, inference=True)
        return score.item()
