"""
C2PA(콘텐츠 출처 및 진위 확인) 분석 모듈
PNG/JPEG 이미지의 메타데이터에서 C2PA Manifest를 추출하고 유효성을 검증합니다.
"""

from __future__ import annotations

import dataclasses
import hashlib
import struct
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import brotli
import cbor2
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

# 신뢰할 수 있는 중간 CA 지문 (SHA-256)
TRUSTED_INTERMEDIATE_FPS = {
    "e2202c12c00880ddfe53af5e787c0431abb6dc566382886ac5540789ffc912d9",  # Truepic WebClaimSigningCA
    "1e92ec6f4c801736ee024905210c4cb95fe4e2a42f404bdb5cc772b12336a6d9",  # Microsoft SCD Claimants RSA CA
    "24213596a832efb823864eacf5b2428c3d472435e38991cd805ce72af4bb9924",  # Google C2PA Media Services 1P ICA G3
}

PNG_SIG = b"\x89PNG\r\n\x1a\n"
JPG_SOI = b"\xff\xd8"
MAX_VARCHAR = 100
MAX_BOX_DEPTH = 20  # JUMBF 재귀 깊이 제한 (Stack Overflow 방지)
MAX_DECOMPRESSED_SIZE = 10 * 1024 * 1024  # Brotli 최대 해제 크기 제한 (10MB, DoS 방지)

# --- Utility Functions ---

def be16(b: bytes) -> int:
    return struct.unpack(">H", b)[0]

def be32(b: bytes) -> int:
    return struct.unpack(">I", b)[0]

def be64(b: bytes) -> int:
    return struct.unpack(">Q", b)[0]

def is_bytes32(x: Any) -> bool:
    return isinstance(x, (bytes, bytearray)) and len(x) == 32

def trunc(s: Optional[str], maxlen: int = MAX_VARCHAR) -> Optional[str]:
    if s is None:
        return None
    s = str(s)
    return s if len(s) <= maxlen else s[: maxlen - 1] + "…"

def agent_name(sa: Any) -> Optional[str]:
    if isinstance(sa, dict) and isinstance(sa.get("name"), str):
        return sa["name"]
    if isinstance(sa, str):
        return sa
    return None

# --- PNG/JPEG Parsing ---

@dataclass
class PngChunk:
    type: str
    chunk_offset: int
    data_offset: int
    data_length: int
    total_length: int
    data: memoryview

def parse_png_chunks(png_bytes: bytes) -> List[PngChunk]:
    if not png_bytes.startswith(PNG_SIG):
        raise ValueError("Not a PNG file")
    chunks: List[PngChunk] = []
    i = 8
    n = len(png_bytes)
    while i + 12 <= n:
        length = be32(png_bytes[i : i + 4])
        ctype = png_bytes[i + 4 : i + 8].decode("ascii", errors="replace")
        data_off = i + 8
        crc_off = data_off + length
        total = 12 + length
        if crc_off + 4 > n:
            break
        chunks.append(
            PngChunk(
                type=ctype,
                chunk_offset=i,
                data_offset=data_off,
                data_length=length,
                total_length=total,
                data=memoryview(png_bytes)[data_off : data_off + length],
            )
        )
        i = crc_off + 4
        if ctype == "IEND":
            break
    return chunks

@dataclass
class JpegPart:
    name: str
    start: int
    end: int
    data: memoryview

JPEG_MARKER_NAMES = {
    0xD8: "SOI", 0xD9: "EOI", 0xDA: "SOS", 0xDB: "DQT",
    0xC0: "SOF0", 0xC2: "SOF2", 0xC4: "DHT", 0xDD: "DRI", 0xFE: "COM",
    0xE0: "APP0", 0xE1: "APP1", 0xE2: "APP2", 0xE3: "APP3", 0xE4: "APP4",
    0xE5: "APP5", 0xE6: "APP6", 0xE7: "APP7", 0xE8: "APP8", 0xE9: "APP9",
    0xEA: "APP10", 0xEB: "APP11", 0xEC: "APP12", 0xED: "APP13", 0xEE: "APP14",
    0xEF: "APP15",
}

def parse_jpeg_parts(jpg: bytes) -> Tuple[List[JpegPart], List[bytes]]:
    if not jpg.startswith(JPG_SOI):
        raise ValueError("Not a JPEG (missing SOI)")
    parts: List[JpegPart] = []
    c2pa_payloads: List[bytes] = []

    n = len(jpg)
    i = 0
    parts.append(JpegPart("SOI", 0, 2, memoryview(jpg)[0:2]))
    i = 2

    while i < n:
        if jpg[i] != 0xFF:
            i += 1
            continue
        j = i
        while j < n and jpg[j] == 0xFF:
            j += 1
        if j >= n:
            break
        marker = jpg[j]
        i = j + 1

        if marker == 0xD9:
            parts.append(JpegPart("EOI", j - 1, j + 1, memoryview(jpg)[j - 1 : j + 1]))
            break
        if 0xD0 <= marker <= 0xD7:
            parts.append(JpegPart(f"RST{marker-0xD0}", j - 1, j + 1, memoryview(jpg)[j - 1 : j + 1]))
            continue
        if marker in (0xD8, 0x01):
            name = JPEG_MARKER_NAMES.get(marker, f"MRK{marker:02X}")
            parts.append(JpegPart(name, j - 1, j + 1, memoryview(jpg)[j - 1 : j + 1]))
            continue

        if i + 2 > n:
            break
        seglen = be16(jpg[i : i + 2])
        seg_start = j - 1
        seg_end = i + seglen
        if seg_end > n:
            break

        payload = jpg[i + 2 : seg_end]
        name = JPEG_MARKER_NAMES.get(marker, f"MRK{marker:02X}")

        if marker == 0xEB and payload.startswith(b"C2PA"):
            name = "C2PA"
            c2pa_payloads.append(payload)
        elif marker == 0xEB:
            name = "APP11"

        parts.append(JpegPart(name, seg_start, seg_end, memoryview(jpg)[seg_start:seg_end]))
        if marker == 0xDA:
            break
        i = seg_end

    return parts, c2pa_payloads

# --- JUMBF/CBOR Analysis ---

@dataclass
class Box:
    boxtype: str
    offset: int
    size: int
    header_size: int
    payload_offset: int
    payload_size: int
    payload: memoryview
    children: List["Box"] = dataclasses.field(default_factory=list)

def parse_boxes(buf: bytes, start: int = 0, end: Optional[int] = None, depth: int = 0) -> List[Box]:
    if depth > MAX_BOX_DEPTH:
        logging.warning("Maximum JUMBF box recursion depth exceeded. Potential DoS attempt.")
        return []

    if end is None:
        end = len(buf)
    boxes: List[Box] = []
    i = start
    while i + 8 <= end:
        size32 = be32(buf[i : i + 4])
        typ = buf[i + 4 : i + 8].decode("ascii", errors="replace")
        header = 8
        size = size32
        if size32 == 1:
            if i + 16 > end: break
            size = be64(buf[i + 8 : i + 16])
            header = 16
        elif size32 == 0:
            size = end - i
        if size < header or i + size > end: break
        payload_off = i + header
        payload_size = size - header
        payload = memoryview(buf)[payload_off : payload_off + payload_size]
        box = Box(typ, i, size, header, payload_off, payload_size, payload)
        
        if typ == "jumb":
            box.children = parse_boxes(buf, payload_off, payload_off + payload_size, depth + 1)
        if typ == "brob":
            try:
                # Brotli Bomb(DoS) 방지를 위해 청크 단위 제한적 압축 해제
                dec = brotli.Decompressor()
                decomp = bytearray()
                for chunk_idx in range(0, len(payload), 4096):
                    decomp.extend(dec.process(payload.tobytes()[chunk_idx:chunk_idx+4096]))
                    if len(decomp) > MAX_DECOMPRESSED_SIZE:
                        raise ValueError("Brotli payload exceeded size limit (DoS prevention)")
                
                box.children = parse_boxes(bytes(decomp), 0, len(decomp), depth + 1)
            except Exception as e:
                logging.error(f"Brotli decompression failed: {e}", exc_info=True)
                box.children = []
                
        boxes.append(box)
        i += size
    return boxes

def parse_jumd_label(jumd_payload: bytes) -> Optional[str]:
    if len(jumd_payload) < 17: return None
    label_bytes = jumd_payload[17:]
    nul = label_bytes.find(b"\x00")
    if nul >= 0: label_bytes = label_bytes[:nul]
    return label_bytes.decode("utf-8", errors="replace") if label_bytes else None

def jumb_label(jumb: Box) -> Optional[str]:
    for ch in jumb.children:
        if ch.boxtype == "jumd":
            return parse_jumd_label(ch.payload.tobytes())
    return None

@dataclass
class CborNode:
    label_path: Tuple[str, ...]
    payload_bytes: bytes
    decoded: Any

def collect_cbor_nodes(root_boxes: List[Box]) -> List[CborNode]:
    nodes: List[CborNode] = []
    def walk(cur_boxes: List[Box], labels: List[str]):
        for b in cur_boxes:
            if b.boxtype == "jumb":
                lab = jumb_label(b) or "<unlabeled>"
                walk(b.children, labels + [lab])
                continue
            if b.boxtype == "cbor":
                pb = b.payload.tobytes()
                try:
                    dec = cbor2.loads(pb)
                    nodes.append(CborNode(tuple(labels), pb, dec))
                except Exception as e:
                    logging.error(f"CBOR parse error: {e}", exc_info=True)
                    continue
            if b.children:
                walk(b.children, labels)
    walk(root_boxes, [])
    return nodes

# --- COSE / Binding Verification ---

def verify_cose_sign1(tag18_obj: cbor2.CBORTag, claim_bytes: bytes) -> Tuple[bool, Optional[Dict], str]:
    try:
        arr = tag18_obj.value
        protected, unprotected, payload_in_sig, sig = arr
        prot_map = cbor2.loads(protected) if protected else {}
        
        # x5chain (key 33)
        chain = prot_map.get(33) or unprotected.get(33) or prot_map.get("x5chain") or unprotected.get("x5chain")
        if not chain: return False, None, "x5chain not found"
        
        leaf = x509.load_der_x509_certificate(chain[0])
        intermediate_fp = None
        if len(chain) >= 2:
            inter = x509.load_der_x509_certificate(chain[1])
            intermediate_fp = inter.fingerprint(hashes.SHA256()).hex()
            
            # Leaf Certificate가 Intermediate CA로부터 발급되었는지 서명 검증 (보안 강화)
            try:
                inter_pub = inter.public_key()
                if isinstance(inter_pub, rsa.RSAPublicKey):
                    inter_pub.verify(
                        leaf.signature,
                        leaf.tbs_certificate_bytes,
                        padding.PKCS1v15(),
                        leaf.signature_hash_algorithm
                    )
                elif isinstance(inter_pub, ec.EllipticCurvePublicKey):
                    inter_pub.verify(
                        leaf.signature,
                        leaf.tbs_certificate_bytes,
                        ec.ECDSA(leaf.signature_hash_algorithm)
                    )
                else:
                    return False, None, "Unsupported intermediate public key type"
            except Exception as e:
                logging.error(f"Certificate chain validation failed: {e}", exc_info=True)
                return False, None, "Leaf certificate not properly issued by intermediate"
            
        alg = prot_map.get(1) or unprotected.get(1)
        signer_info = {
            "subject": leaf.subject.rfc4514_string(),
            "issuer": leaf.issuer.rfc4514_string(),
            "intermediate_fp256": intermediate_fp
        }
        
        payload = payload_in_sig if payload_in_sig is not None else claim_bytes
        to_be_signed = cbor2.dumps(["Signature1", protected, b"", payload], canonical=True)
        pub = leaf.public_key()
        
        if alg == -7: # ES256
            r, s = int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")
            pub.verify(encode_dss_signature(r, s), to_be_signed, ec.ECDSA(hashes.SHA256()))
        elif alg == -37: # PS256
            pub.verify(sig, to_be_signed, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
        else:
            return False, signer_info, f"unsupported alg {alg}"
            
        return True, signer_info, "ok"
    except Exception as e:
        return False, None, str(e)

def hash_data_verify(file_bytes: bytes, hash_data_obj: Dict) -> bool:
    if hash_data_obj.get("alg") != "sha256": return False
    expected = hash_data_obj.get("hash")
    if not is_bytes32(expected): return False
    
    # C2PA Exclusions 로직 적용 (서명 영역 등을 해시에서 제외)
    h = hashlib.sha256()
    exclusions = hash_data_obj.get("exclusions", [])
    # start 값 기준으로 오름차순 정렬
    sorted_exclusions = sorted(exclusions, key=lambda x: x.get("start", 0))
    
    pos = 0
    for exc in sorted_exclusions:
        start = exc.get("start", 0)
        length = exc.get("length", 0)
        
        if start > pos:
            h.update(file_bytes[pos:start])
        pos = start + length
        
    if pos < len(file_bytes):
        h.update(file_bytes[pos:])
        
    return h.digest() == bytes(expected)

# --- Action Parsing ---

def parse_actions(actions_obj: Dict) -> Dict:
    out = {"ai_declared": False, "created_model": None, "converted_model": None, "created_description": None,
           "total_dst": None, "synth_id": None, "synth_id_dst": None, "visible_wm": None, "visible_wm_dst": None}
    actions = actions_obj.get("actions", [])
    for a in actions:
        act = a.get("action")
        desc = a.get("description")
        dst = a.get("digitalSourceType")
        sa = agent_name(a.get("softwareAgent"))
        if act == "c2pa.created":
            if dst:
                out["total_dst"] = out["total_dst"] or dst
                if dst.endswith("/trainedAlgorithmicMedia"): out["ai_declared"] = True
            if sa: out["created_model"] = out["created_model"] or sa
            if desc: out["created_description"] = out["created_description"] or desc
        elif act == "c2pa.converted":
            if sa: out["converted_model"] = out["converted_model"] or sa
        elif act == "c2pa.edited" and desc:
            if "synthid" in desc.lower():
                out["synth_id"], out["synth_id_dst"] = desc, dst
            if "visible watermark" in desc.lower():
                out["visible_wm"], out["visible_wm_dst"] = desc, dst
    return out

# --- Main Class ---

class C2PAAnalyzer:
    @staticmethod
    def analyze_image(image_path: str) -> Dict[str, Any]:
        p = Path(image_path)
        if not p.exists(): return {"is_c2pa_compliant": False}
        file_bytes = p.read_bytes()
        
        kind = "png" if file_bytes.startswith(PNG_SIG) else "jpg" if file_bytes.startswith(JPG_SOI) else "unknown"
        if kind == "unknown": return {"is_c2pa_compliant": False}

        stores = []
        if kind == "png":
            for c in parse_png_chunks(file_bytes):
                if c.type == "caBX": stores.append(c.data.tobytes())
        else:
            _, payloads = parse_jpeg_parts(file_bytes)
            if payloads:
                # 여러 개의 C2PA 매니페스트 APP11 세그먼트를 개별적으로 처리
                for p_data in payloads:
                    stream = p_data[4:] if p_data.startswith(b"C2PA") else p_data
                    jpos = stream.find(b"jumb")
                    if jpos >= 4:
                        stores.append(stream[jpos-4:])

        if not stores: return {"is_c2pa_compliant": False}

        all_manifests = []
        for s in stores:
            nodes = collect_cbor_nodes(parse_boxes(s))
            idx = {}
            for n in nodes:
                if len(n.label_path) >= 2:
                    urn = n.label_path[1]
                    idx.setdefault(urn, {})[n.label_path[-1]] = n
            
            for urn, m in idx.items():
                claim_node = m.get("c2pa.claim.v2")
                if not claim_node: continue
                
                sig_ok, signer, _ = verify_cose_sign1(m["c2pa.signature"].decoded, claim_node.payload_bytes) if "c2pa.signature" in m else (False, None, "")
                binding_ok = hash_data_verify(file_bytes, m["c2pa.hash.data"].decoded) if "c2pa.hash.data" in m else False
                
                actions = parse_actions(m["c2pa.actions.v2"].decoded) if "c2pa.actions.v2" in m else {}
                
                trusted = signer["intermediate_fp256"] in TRUSTED_INTERMEDIATE_FPS if signer else False
                
                all_manifests.append({
                    "compliant": sig_ok and binding_ok and actions.get("ai_declared") and trusted,
                    "score": (50 if actions.get("ai_declared") else 0) + (20 if sig_ok else 0) + (20 if binding_ok else 0),
                    "actions": actions,
                    "claim_generator": claim_node.decoded.get("claim_generator")
                })

        if not all_manifests: return {"is_c2pa_compliant": False}
        
        best = max(all_manifests, key=lambda x: x["score"])
        any_ok = any(m["compliant"] for m in all_manifests)
        
        return {
            "is_c2pa_compliant": any_ok,
            "created_model": trunc(best["actions"]["created_model"]),
            "converted_model": trunc(best["actions"]["converted_model"]),
            "created_description": trunc(best["actions"]["created_description"]),
            "claim_generator": trunc(best["claim_generator"]),
            "claim_generator_info_name": None,
            "synth_id": trunc(best["actions"]["synth_id"]),
            "visible_watermark": trunc(best["actions"]["visible_wm"]),
            "total_digital_source_type": trunc(best["actions"]["total_dst"]),
            "synth_id_digital_source_type": trunc(best["actions"]["synth_id_dst"]),
            "visible_watermark_digital_source_type": trunc(best["actions"]["visible_wm_dst"])
        }