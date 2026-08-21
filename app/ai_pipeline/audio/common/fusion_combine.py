"""
음성/가창 두 트랙이 공유하는 fusion 결합 로직. heimdall-vox의 fit_fusion.py가 저장하는
각 method별 파라미터 형태를 그대로 재현한다 (FUSION.md 참고).

method를 하드코딩하지 않고 fusion JSON에서 분기하는 이유: heimdall-vox 쪽 K-Fold 재검증
결과에 따라 최종 방식이 이미 한 번 바뀐 적이 있다 (음성 트랙: logreg_C10.0 -> soft_voting).
"""
import math
from typing import Any, Dict, List


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def calibrate(raw_scores: Dict[str, float], fusion: Dict[str, Any], order: List[str]) -> Dict[str, float]:
    """모델별 raw_score(logit)를 Platt scaling으로 보정: calibrated = sigmoid(a * raw + b)."""
    calibrated = {}
    for i, name in enumerate(order):
        cal = fusion["calibration"][i]
        calibrated[name] = sigmoid(cal["a"] * raw_scores[name] + cal["b"])
    return calibrated


def combine_scores(calibrated: Dict[str, float], fusion: Dict[str, Any], order: List[str]) -> float:
    """simple_mean/fixed_weighted/soft_voting은 보정된 확률의 (가중) 평균이고,
    logreg_C*만 로지스틱 회귀라 sigmoid(intercept + sum(coef*x)) 형태가 다르다."""
    method = fusion["method"]

    if method == "simple_mean":
        return sum(calibrated[name] for name in order) / len(order)

    if method in ("fixed_weighted", "soft_voting"):
        return sum(fusion["weights"][name] * calibrated[name] for name in order)

    if method.startswith("logreg_C"):
        z = fusion["logreg_intercept"]
        for name in order:
            z += fusion["logreg_coef"][name] * calibrated[name]
        return sigmoid(z)

    raise ValueError(f"알 수 없는 fusion method: {method!r}")
