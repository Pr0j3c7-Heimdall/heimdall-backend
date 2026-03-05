"""
C2PA(콘텐츠 출처 및 진위 확인) 분석 모듈
c2patool.exe를 사용하여 이미지의 C2PA Manifest를 추출하고 유효성을 검증합니다.
"""

from __future__ import annotations

import json
import re
import subprocess
import logging
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 현재 파일이 위치한 폴더를 기준으로 모든 도구 경로 설정 (app/ai_pipeline/image/c2pa/)
BASE_DIR = Path(__file__).parent.resolve()

# 환경에 따른 실행 파일 이름 결정 (윈도우: .exe, 리눅스/WSL: 확장자 없음)
IS_WINDOWS = sys.platform.startswith("win32")
TOOL_FILENAME = "c2patool.exe" if IS_WINDOWS else "c2patool"

C2PATOOL_EXE = str(BASE_DIR / TOOL_FILENAME)
TRUST_ANCHORS = str(BASE_DIR / "anchors.pem")
TARGET_DST = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"

# 로그에 현재 환경 정보 기록
logging.info(f"C2PA: Platform: {sys.platform} (OS: {os.name})")
logging.info(f"C2PA: Base directory (BASE_DIR): {BASE_DIR}")
logging.info(f"C2PA: Using tool at (C2PATOOL_EXE): {C2PATOOL_EXE}")
logging.info(f"C2PA: Using trust anchors at (TRUST_ANCHORS): {TRUST_ANCHORS}")

# --- Helper Functions ---

def run_cmd(args: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """외부 명령어를 실행하고 결과를 반환합니다."""
    if IS_WINDOWS:
        cmd_str = " ".join(f'"{arg}"' for arg in args)
        shell_val = True
    else:
        cmd_str = args
        shell_val = False
    
    logging.info(f"C2PA: Executing command: {cmd_str}")
    logging.info(f"C2PA: In working directory (cwd): {cwd}")
    
    proc = subprocess.run(
        cmd_str,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=shell_val,
        cwd=cwd
    )
    return proc.returncode, proc.stdout, proc.stderr
        

class NoC2PAClaimError(Exception):
    """자산에 C2PA 클레임/매니페스트 스토어가 없을 때 발생합니다."""
    pass

def is_no_claim_found(stderr_text: str) -> bool:
    """에러 출력에서 C2PA 클레임을 찾지 못했다는 메시지가 있는지 확인합니다."""
    t = (stderr_text or "").lower()
    return (
        "no claim found" in t
        or "no manifest store found" in t
        or "no manifest found" in t
    )

def extract_json_from_mixed_output(s: str) -> Any:
    """텍스트 출력에서 JSON 부분을 찾아 파싱합니다."""
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

    raise ValueError("Failed to parse JSON from c2patool output")

def normalize_trust_arg(path_or_url: str) -> str:
    """신뢰 앵커 경로를 정규화합니다."""
    s = path_or_url.strip()
    if not s:
        return s
    
    # 웹 URL(http, https)인 경우에만 그대로 반환
    if re.match(r"^(http|https)://", s.lower()):
        return s
        
    # 로컬 경로인 경우 file:/// 변환 없이 순수한 절대 경로 문자열로 반환
    p = Path(s)
    return str(p.resolve())

# --- Manifest Parsing Logic ---

def safe_str(x: Any) -> Optional[str]:
    """입력이 문자열인 경우에만 반환합니다."""
    return x if isinstance(x, str) else None

def software_agent_name(sa: Any) -> Optional[str]:
    """SoftwareAgent 정보에서 이름을 추출합니다."""
    if isinstance(sa, dict):
        return safe_str(sa.get("name"))
    if isinstance(sa, str):
        return sa
    return None

def walk_find_actions(obj: Any) -> List[Dict[str, Any]]:
    """Manifest 구조를 순회하며 모든 action 항목을 찾아 리스트로 반환합니다."""
    found: List[Dict[str, Any]] = []

    def rec(x: Any):
        if isinstance(x, dict):
            if "actions" in x and isinstance(x["actions"], list):
                ok = True
                for it in x["actions"]:
                    if not (isinstance(it, dict) and "action" in it):
                        ok = False
                        break
                if ok:
                    for it in x["actions"]:
                        found.append(it)
            for v in x.values():
                rec(v)
        elif isinstance(x, list):
            for it in x:
                rec(it)

    rec(obj)
    return found

def get_manifest_store(report: Dict[str, Any]) -> Dict[str, Any]:
    """보고서에서 manifest_store 객체를 안전하게 추출합니다."""
    if isinstance(report.get("manifest_store"), dict):
        return report["manifest_store"]
    return report

def pick_claim_fields(manifest_obj: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """매니페스트 객체에서 claim_generator 정보를 추출합니다."""
    claim_generator = None
    claim_generator_info_name = None

    candidates = [manifest_obj]
    if isinstance(manifest_obj.get("claim"), dict):
        candidates.append(manifest_obj["claim"])

    for c in candidates:
        if claim_generator is None:
            claim_generator = safe_str(c.get("claim_generator"))
        cgi = c.get("claim_generator_info")
        if claim_generator_info_name is None:
            if isinstance(cgi, dict):
                claim_generator_info_name = safe_str(cgi.get("name"))
            elif isinstance(cgi, list) and cgi:
                first = cgi[0]
                if isinstance(first, dict):
                    claim_generator_info_name = safe_str(first.get("name"))

    return claim_generator, claim_generator_info_name

def extract_fields_from_report(report: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """전체 C2PA 보고서에서 필요한 주요 필드들을 추출합니다."""
    ms = get_manifest_store(report)
    manifests = ms.get("manifests") if isinstance(ms, dict) else None
    if not isinstance(manifests, dict):
        manifests = {}

    actions_all = walk_find_actions(report)

    created_model = None
    converted_model = None
    created_description = None
    total_digital_source_type = None
    synth_id = None
    synth_id_dst = None
    visible_wm = None
    visible_wm_dst = None
    ai_declared = False

    for a in actions_all:
        if not isinstance(a, dict):
            continue
        act = safe_str(a.get("action"))
        desc = safe_str(a.get("description"))
        dst = safe_str(a.get("digitalSourceType"))
        sa = software_agent_name(a.get("softwareAgent"))

        if act == "c2pa.created":
            if total_digital_source_type is None and dst:
                total_digital_source_type = dst
            if dst == TARGET_DST:
                ai_declared = True
            if created_model is None and sa:
                created_model = sa
            if created_description is None and desc:
                created_description = desc
        elif act == "c2pa.converted":
            if converted_model is None and sa:
                converted_model = sa
        elif act == "c2pa.edited":
            if desc:
                lo = desc.lower()
                if synth_id is None and "synthid" in lo:
                    synth_id = desc
                    synth_id_dst = dst
                if visible_wm is None and "visible watermark" in lo:
                    visible_wm = desc
                    visible_wm_dst = dst

    active = safe_str(ms.get("active_manifest")) if isinstance(ms, dict) else None
    claim_generator = None
    claim_generator_info_name = None

    if active and active in manifests and isinstance(manifests[active], dict):
        claim_generator, claim_generator_info_name = pick_claim_fields(manifests[active])

    if claim_generator is None or claim_generator_info_name is None:
        for m in manifests.values():
            if isinstance(m, dict):
                cg, cgi = pick_claim_fields(m)
                if claim_generator is None and cg:
                    claim_generator = cg
                if claim_generator_info_name is None and cgi:
                    claim_generator_info_name = cgi
            if claim_generator and claim_generator_info_name:
                break

    return {
        "created_model": created_model,
        "converted_model": converted_model,
        "created_description": created_description,
        "claim_generator": claim_generator,
        "claim_generator_info_name": claim_generator_info_name,
        "synth_id": synth_id,
        "visible_watermark": visible_wm,
        "total_digital_source_type": total_digital_source_type,
        "synth_id_digital_source_type": synth_id_dst,
        "visible_watermark_digital_source_type": visible_wm_dst,
        "ai_declared": ai_declared,
    }

# --- Validation Logic ---

SIGNATURE_FAIL_CODES = {
    "signingCredential.invalid", "signingCredential.revoked", "signingCredential.expired",
    "timeStamp.mismatch", "timeStamp.untrusted", "timeStamp.outsideValidity",
}
BINDING_FAIL_HINTS = ("assertion.", "manifest.", "ingredient.", "hash.")

def classify_validation_status(vs: Any, validation_state: Optional[str]) -> Tuple[bool, bool, bool, List[str]]:
    """검증 상태 코드를 분석하여 서명, 바인딩, 신뢰 여부를 판별합니다."""
    if isinstance(validation_state, str) and validation_state.lower() == "trusted" and vs is None:
        return True, True, True, []

    codes: List[str] = []
    if vs is None:
        return True, True, True, codes

    if isinstance(vs, list):
        for it in vs:
            if isinstance(it, dict) and isinstance(it.get("code"), str):
                codes.append(it["code"])
    elif isinstance(vs, dict) and isinstance(vs.get("code"), str):
        codes.append(vs["code"])

    trusted_signer = True
    signature_ok = True
    binding_ok = True

    for c in codes:
        if c == "signingCredential.untrusted":
            trusted_signer = False
        if c in SIGNATURE_FAIL_CODES or c.startswith("claimSignature."):
            signature_ok = False
        if any(c.startswith(h) for h in BINDING_FAIL_HINTS) and ("mismatch" in c or "invalid" in c):
            binding_ok = False

    return signature_ok, binding_ok, trusted_signer, codes

# --- C2PAAnalyzer Class ---

class C2PAAnalyzer:
    @staticmethod
    def analyze_image(image_path: str) -> Dict[str, Any]:
        """이미지를 분석하여 C2PA 준수 여부 및 관련 메타데이터를 추출합니다."""
        p = Path(image_path)
        logging.info(f"C2PA: Analyzing image at {image_path}")
        logging.info(f"C2PA: Using tool at {C2PATOOL_EXE}")
        
        default_res = {
            "is_c2pa_compliant": False,
            "created_model": None,
            "converted_model": None,
            "created_description": None,
            "claim_generator": None,
            "claim_generator_info_name": None,
            "synth_id": None,
            "visible_watermark": None,
            "total_digital_source_type": None,
            "synth_id_digital_source_type": None,
            "visible_watermark_digital_source_type": None
        }
        
        if not p.exists():
            logging.error(f"C2PA: Image file not found: {image_path}")
            return default_res

        abs_image_path = str(p.resolve())

        try:
            # 1. Manifest JSON 추출
            rc, out, err = run_cmd([C2PATOOL_EXE, abs_image_path], cwd=str(BASE_DIR))
            logging.info(f"C2PA: Manifest extraction RC={rc}")
            if rc != 0:
                if is_no_claim_found(err):
                    logging.info("C2PA: No C2PA claim found in image.")
                    return default_res
                logging.error(f"C2PA: c2patool failed rc={rc}: {err}")
                return default_res
            
            logging.info(f"C2PA: Manifest output (first 200 chars): {out[:200]}")
            report = extract_json_from_mixed_output(out)
            fields = extract_fields_from_report(report)
            ai_declared = fields.pop("ai_declared", False)
            logging.info(f"C2PA: AI declared: {ai_declared}")

            # 2. Trust 검증
            ta = normalize_trust_arg(TRUST_ANCHORS)
            logging.info(f"C2PA: Using trust anchors at {ta}")
            t_rc, t_out, t_err = run_cmd([C2PATOOL_EXE, abs_image_path, "trust", "--trust_anchors", ta], cwd=str(BASE_DIR))
            logging.info(f"C2PA: Trust validation RC={t_rc}")
            
            if t_rc != 0:
                logging.error(f"C2PA: c2patool trust failed rc={t_rc}: {t_err}")
                return {**default_res, **fields, "is_c2pa_compliant": False}

            logging.info(f"C2PA: Trust output (first 200 chars): {t_out[:200]}")
            trust_report = extract_json_from_mixed_output(t_out)
            ms_t = get_manifest_store(trust_report)

            validation_status = ms_t.get("validation_status", trust_report.get("validation_status"))
            validation_state = ms_t.get("validation_state", trust_report.get("validation_state"))

            sig_ok, bind_ok, trusted, codes = classify_validation_status(validation_status, validation_state)
            logging.info(f"C2PA: sig_ok={sig_ok}, bind_ok={bind_ok}, trusted={trusted}, codes={codes}")

            is_compliant = (sig_ok and bind_ok and trusted and ai_declared)
            logging.info(f"C2PA: Final compliant status: {is_compliant}")

            return {
                "is_c2pa_compliant": is_compliant,
                "created_model": fields["created_model"],
                "converted_model": fields["converted_model"],
                "created_description": fields["created_description"],
                "claim_generator": fields["claim_generator"],
                "claim_generator_info_name": fields["claim_generator_info_name"],
                "synth_id": fields["synth_id"],
                "visible_watermark": fields["visible_watermark"],
                "total_digital_source_type": fields["total_digital_source_type"],
                "synth_id_digital_source_type": fields["synth_id_digital_source_type"],
                "visible_watermark_digital_source_type": fields["visible_watermark_digital_source_type"]
            }

        except Exception as e:
            logging.error(f"C2PA: Error during analysis: {e}", exc_info=True)
            return default_res
