import json
import subprocess
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, List

# ExifTool 결과에서 제거할 기본 태그들
DEFAULT_EXCLUDE_TAGS: Set[str] = {
    "ExifToolVersion",
    "Directory",
    "FilePermissions",
    "SourceFile",
}

def _base_tag(tag: str) -> str:
    """그룹 접두사가 붙은 태그에서 실제 태그명만 추출"""
    return tag.split(":")[-1]

def run_cmd(args: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """외부 명령어를 실행하고 결과를 반환합니다. (c2pa_analyzer 패턴 공유)"""
    logging.info(f"Metadata: Executing command: {args}")
    
    proc = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,  # 보안을 위해 명시적으로 False 설정
        cwd=cwd
    )
    return proc.returncode, proc.stdout, proc.stderr

def extract_json_from_mixed_output(s: str) -> Any:
    """텍스트 출력에서 JSON 부분을 찾아 파싱합니다. (c2pa_analyzer 패턴 공유)"""
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        pass

    start_o = s.find("{")
    end_o = s.rfind("}")
    if start_o != -1 and end_o != -1 and end_o > start_o:
        return json.loads(s[start_o:end_o + 1])

    start_a = s.find("[")
    end_a = s.rfind("]")
    if start_a != -1 and end_a != -1 and end_a > start_a:
        return json.loads(s[start_a:end_a + 1])

    raise ValueError("Failed to parse JSON from exiftool output")

def run_exiftool_json(
    image_path: str | Path,
    exiftool_bin: str = "exiftool"
) -> Dict[str, Any]:
    """ExifTool을 실행하여 메타데이터를 JSON으로 가져옵니다."""
    p = Path(image_path)
    if not p.exists():
        logging.error(f"Metadata: Image file not found: {image_path}")
        return {}

    abs_image_path = str(p.resolve())
    
    cmd = [
        exiftool_bin,
        "-json",
        "-struct",
        "-charset", "filename=utf8",
        abs_image_path,
    ]

    try:
        rc, out, err = run_cmd(cmd)
        
        if rc != 0:
            logging.error(f"Metadata: ExifTool failed (rc={rc}): {err}")
            return {}

        payload = extract_json_from_mixed_output(out)
        if isinstance(payload, list) and payload:
            return payload[0]
        elif isinstance(payload, dict):
            return payload
    except Exception as e:
        logging.error(f"Metadata: Error running ExifTool: {e}")
    
    return {}

def filter_metadata(
    meta: Dict[str, Any],
    exclude_tags: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """불필요한 태그를 필터링합니다."""
    exclude_tags = exclude_tags or DEFAULT_EXCLUDE_TAGS
    filtered: Dict[str, Any] = {}
    for k, v in meta.items():
        if k in exclude_tags or _base_tag(k) in exclude_tags:
            continue
        filtered[k] = v
    return filtered

async def extract_metadata(image_path: str) -> Dict[str, Any]:
    """
    비동기 파이프라인에서 호출할 메타데이터 추출 함수입니다.
    """
    loop = asyncio.get_event_loop()
    # 블로킹 함수인 run_exiftool_json을 executor에서 처리
    raw_meta = await loop.run_in_executor(None, run_exiftool_json, image_path)
    if not raw_meta:
        return {}
        
    return filter_metadata(raw_meta)
