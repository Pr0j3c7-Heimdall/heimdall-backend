"""
YAMNet 기반 음성/가창/예외 자동 판별 (프레임워크의 "Type 판별 조건" 단계).

heimdall-vox 쪽에서 900개 샘플(클래스당 300개, speech/singing/other)로 검증한
그룹 매핑과 스코어링 로직을 그대로 이식했다. 그룹 구성이나 other_scoring 로직을
바꾸면 검증된 정확도가 깨지므로, 바꿀 경우 threshold를 다시 탐색해야 한다.

TFLite로 내보낸 공식 YAMNet(https://tfhub.dev/google/yamnet/1)은 TF-Hub SavedModel과
동일하게 (num_samples,) 형태의 가변 길이 waveform을 입력받아 0.96초 윈도우/0.48초 hop으로
내부 프레이밍을 수행하고 (num_frames, 521) 점수를 반환한다 — 즉 아래 로직은 원래 threshold를
산출할 때 쓴 hub.load() 버전과 프레임 단위로 동일하게 동작한다.

판정 규칙 (Type 판별 조건):
  a: s1 >= MIN_CONFIDENCE
  b: s1 - s2 >= MIN_MARGIN
  confirmed = a and b 이고, 이때 top1이 speech/singing이면 해당 트랙으로 확정한다.
  그 외(confirmed가 아니거나 top1이 other로 확정된 경우)는 모두 예외로 라우팅한다 —
  프레임워크가 성공 시 음성/가창 두 갈래로만 분기하고 실패 시 예외 하나로 합치는 것과 대응.
"""
import asyncio
import csv
import logging
import math
import os
from typing import Dict, List, Optional, Sequence

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

try:
    # requirements.txt는 ai-edge-litert를 설치한다 — tflite-runtime은 PyPI에 cp312 wheel이
    # 없어(Dockerfile 베이스가 Python 3.12) 이 이미지에서 설치가 안 된다. tflite-runtime을
    # 먼저 시도하는 이유는 순수 CPU 환경에서 그쪽이 더 가벼워, 다른 배포 대상(Python<=3.11)에서
    # 그 패키지를 쓰는 경우를 자동으로 지원하기 위함이다.
    from tflite_runtime.interpreter import Interpreter
except ImportError:
    try:
        from ai_edge_litert.interpreter import Interpreter
    except ImportError as e:  # 가중치/런타임 미배치 등으로 임포트가 실패해도 서비스는 떠야 한다
        logging.error(f"Import error (YAMNet TFLite Interpreter): {e}", exc_info=True)
        Interpreter = None

SAMPLE_RATE = 16000
# YAMNet은 첫 프레임 점수를 얻는 데 최소 0.975초 분량의 파형이 필요하다.
MIN_SAMPLES = int(0.975 * SAMPLE_RATE)

# --- Type 판별 임계값 (heimdall-vox 900개 샘플 검증 결과) ---
MIN_CONFIDENCE = 0.16
MIN_MARGIN = 0.15

_YAMNET_DIR = os.path.dirname(os.path.abspath(__file__))
YAMNET_TFLITE_WEIGHTS = os.path.join(_YAMNET_DIR, "yamnet", "weights", "yamnet.tflite")
YAMNET_CLASS_MAP_CSV = os.path.join(_YAMNET_DIR, "yamnet", "yamnet_class_map.csv")

# --- YAMNet 521개 클래스 -> speech/singing/other 그룹 매핑 ---
SPEECH_CLASS_NAMES = [
    "Speech",
    "Child speech, kid speaking",
    "Conversation",
    "Narration, monologue",
    "Babbling",
    "Speech synthesizer",
    "Whispering",
]

SINGING_CLASS_NAMES = [
    "Singing",
    "Choir",
    "Yodeling",
    "Chant",
    "Mantra",
    "Child singing",
    "Synthetic singing",
    "Rapping",
    "Humming",
    "Opera",
    "Vocal music",
    "A capella",
]

OTHER_INSTRUMENT_CLASS_NAMES = [
    "Musical instrument",
    "Guitar",
    "Electric guitar",
    "Bass guitar",
    "Acoustic guitar",
    "Steel guitar, slide guitar",
    "Tapping (guitar technique)",
    "Strum",
    "Banjo",
    "Sitar",
    "Mandolin",
    "Ukulele",
    "Keyboard (musical)",
    "Piano",
    "Electric piano",
    "Organ",
    "Electronic organ",
    "Hammond organ",
    "Synthesizer",
    "Percussion",
    "Drum kit",
    "Drum",
    "Snare drum",
    "Bass drum",
    "Cymbal",
    "Hi-hat",
    "Tambourine",
    "Maraca",
    "Gong",
    "Orchestra",
    "Brass instrument",
    "French horn",
    "Trumpet",
    "Trombone",
    "Bowed string instrument",
    "Violin, fiddle",
    "Cello",
    "Double bass",
    "Wind instrument, woodwind instrument",
    "Flute",
    "Saxophone",
    "Clarinet",
    "Harp",
    "Harmonica",
    "Accordion",
    "Background music",
]

OTHER_EVENT_CLASS_NAMES = [
    "Laughter",
    "Crying, sobbing",
    "Whistling",
    "Breathing",
    "Snoring",
    "Gasp",
    "Pant",
    "Cough",
    "Sneeze",
    "Clapping",
    "Applause",
    "Animal",
    "Domestic animals, pets",
    "Dog",
    "Bark",
    "Cat",
    "Meow",
    "Livestock, farm animals, working animals",
    "Horse",
    "Neigh, whinny",
    "Cowbell",
    "Bird",
    "Bird vocalization, bird call, bird song",
    "Chirp, tweet",
    "Insect",
    "Cricket",
    "Frog",
    "Wind",
    "Rustling leaves",
    "Thunderstorm",
    "Thunder",
    "Water",
    "Rain",
    "Raindrop",
    "Rain on surface",
    "Stream",
    "Waterfall",
    "Ocean",
    "Waves, surf",
    "Fire",
    "Crackle",
    "Vehicle",
    "Car",
    "Vehicle horn, car horn, honking",
    "Truck",
    "Bus",
    "Motorcycle",
    "Train",
    "Aircraft",
    "Helicopter",
    "Engine",
    "Engine starting",
    "Door",
    "Doorbell",
    "Ding-dong",
    "Knock",
    "Tap",
    "Dishes, pots, and pans",
    "Cutlery, silverware",
    "Blender",
    "Vacuum cleaner",
    "Typing",
    "Typewriter",
    "Computer keyboard",
    "Alarm",
    "Alarm clock",
    "Siren",
    "Clock",
    "Tick",
    "Mechanical fan",
    "Air conditioning",
    "Tools",
    "Hammer",
    "Sawing",
    "Power tool",
    "Drill",
    "Explosion",
    "Gunshot, gunfire",
    "Fireworks",
    "Boom",
    "Glass",
    "Shatter",
    "Thump, thud",
    "Breaking",
    "Noise",
    "Static",
    "White noise",
]

# --- 전역 변수로 인터프리터 및 그룹 인덱스 초기화 (프로세스당 1회 로드) ---
_signature_runner = None
_speech_indices: List[int] = []
_singing_indices: List[int] = []
_other_instrument_indices: List[int] = []
_other_event_indices: List[int] = []


def _load_class_names() -> List[str]:
    with open(YAMNET_CLASS_MAP_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row["display_name"] for row in reader]


def _resolve_indices(class_names: Sequence[str], candidates: Sequence[str]) -> List[int]:
    missing = [name for name in candidates if name not in class_names]
    if missing:
        raise RuntimeError(f"YAMNet class map에 없는 클래스: {missing}")
    return [class_names.index(name) for name in candidates]


def init_model() -> None:
    """클래스 그룹 인덱스와 TFLite 인터프리터를 초기화한다.
    가중치가 없으면(심볼릭 링크 미배치) 인터프리터는 None으로 남고,
    classify_audio_type_sync 호출 시 RuntimeError를 낸다(다른 파이프라인과 동일한 방식)."""
    global _signature_runner
    global _speech_indices, _singing_indices, _other_instrument_indices, _other_event_indices

    try:
        class_names = _load_class_names()

        speech = set(_resolve_indices(class_names, SPEECH_CLASS_NAMES))
        singing = set(_resolve_indices(class_names, SINGING_CLASS_NAMES)) - speech
        instrument = set(_resolve_indices(class_names, OTHER_INSTRUMENT_CLASS_NAMES)) - speech - singing
        event = set(_resolve_indices(class_names, OTHER_EVENT_CLASS_NAMES)) - speech - singing

        _speech_indices = sorted(speech)
        _singing_indices = sorted(singing)
        _other_instrument_indices = sorted(instrument)
        _other_event_indices = sorted(event)
    except Exception as e:
        logging.error(f"Error loading YAMNet class map: {e}", exc_info=True)
        return

    if Interpreter is None:
        return

    try:
        if os.path.exists(YAMNET_TFLITE_WEIGHTS):
            interpreter = Interpreter(model_path=YAMNET_TFLITE_WEIGHTS)
            _signature_runner = interpreter.get_signature_runner("serving_default")
    except Exception as e:
        logging.error(f"Error initializing YAMNet TFLite interpreter: {e}", exc_info=True)


init_model()


def _load_waveform_16k(audio_path: str) -> np.ndarray:
    """오디오를 모노 16kHz float32 파형으로 읽는다. YAMNet은 고정 길이를 요구하지
    않으므로(가변 길이 입력) common/audio_preprocessing.py와 달리 crop/pad는 하지 않고
    원본 길이를 유지한 채 필요 시 16kHz로만 리샘플링한다."""
    x, sr = sf.read(audio_path)
    x = np.asarray(x, dtype=np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != SAMPLE_RATE:
        gcd = math.gcd(SAMPLE_RATE, sr)
        x = resample_poly(x, SAMPLE_RATE // gcd, sr // gcd)
    return x.astype(np.float32)


def _group_frame_scores(scores: np.ndarray, indices: Sequence[int]) -> np.ndarray:
    if not indices:
        return np.zeros(scores.shape[0], dtype=np.float32)
    return np.max(scores[:, indices], axis=1)


def _score_file(waveform: np.ndarray) -> Dict[str, float]:
    """speech/singing/other 파일 단위 점수를 낸다. other_instrument는 vocal(speech/singing)
    경쟁 점수를 감산한 뒤 other_event와 max를 취한다 — 반주가 포함된 가창이 악기 라벨 때문에
    other로 잘못 분류되는 것을 완화하기 위함이며, threshold 검증 당시와 동일한 로직이어야 한다."""
    predictions = np.asarray(_signature_runner(waveform=waveform)["predictions"])

    speech_frames = _group_frame_scores(predictions, _speech_indices)
    singing_frames = _group_frame_scores(predictions, _singing_indices)
    other_event_frames = _group_frame_scores(predictions, _other_event_indices)
    other_instrument_raw_frames = _group_frame_scores(predictions, _other_instrument_indices)

    vocal_frames = np.maximum(speech_frames, singing_frames)
    other_instrument_frames = np.clip(other_instrument_raw_frames - vocal_frames, 0.0, 1.0)
    other_frames = np.maximum(other_event_frames, other_instrument_frames)

    return {
        "speech": float(np.mean(speech_frames)),
        "singing": float(np.mean(singing_frames)),
        "other": float(np.mean(other_frames)),
    }


def _decide(scores: Dict[str, float]) -> Optional[str]:
    ranking = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top1_label, s1 = ranking[0]
    _, s2 = ranking[1]

    confirmed = (s1 >= MIN_CONFIDENCE) and (s1 - s2 >= MIN_MARGIN)
    if confirmed and top1_label in ("speech", "singing"):
        return top1_label
    return None


def classify_audio_type_sync(audio_path: str) -> Optional[str]:
    """오디오가 speech/singing 중 무엇인지 판별한다.
    신뢰도·마진 조건을 만족하지 못하거나 top1이 other로 확정되면 None(예외)을 반환한다."""
    if _signature_runner is None:
        raise RuntimeError("YAMNet 모델이 로드되지 않았습니다. init_model()을 확인하세요.")

    waveform = _load_waveform_16k(audio_path)
    if waveform.size < MIN_SAMPLES or not np.all(np.isfinite(waveform)):
        return None

    rms = float(np.sqrt(np.mean(waveform.astype(np.float64) ** 2)))
    if rms < 1e-6:
        return None

    scores = _score_file(waveform)
    return _decide(scores)


async def classify_audio_type(audio_path: str) -> Optional[str]:
    """YAMNet 추론은 동기 블로킹이므로 스레드로 오프로드한다."""
    return await asyncio.to_thread(classify_audio_type_sync, audio_path)
