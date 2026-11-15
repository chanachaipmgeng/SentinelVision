"""Thai National ID & ICAO 9303 TD3 Passport MRZ OCR / Parser Service."""

from __future__ import annotations

import asyncio
import io
import re
from typing import Any, Optional

from fastapi import HTTPException, status

_THAI_ID_RE = re.compile(r"(?<!\d)(\d[\s\-]?\d{4}[\s\-]?\d{5}[\s\-]?\d{2}[\s\-]?\d)(?!\d)")
_MRZ_LINE1_RE = re.compile(r"P[<A-Z0-9][A-Z]{3}[A-Z0-9<]{39}")
_MRZ_LINE2_RE = re.compile(r"[A-Z0-9<]{9}[0-9][A-Z]{3}[0-9]{6}[0-9][MFX<][0-9]{6}[0-9][A-Z0-9<]{14}[0-9<][0-9]")

_ICAO_CHAR_VALUES: dict[str, int] = {str(i): i for i in range(10)}
for _idx, _ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=10):
    _ICAO_CHAR_VALUES[_ch] = _idx
_ICAO_CHAR_VALUES["<"] = 0


def validate_thai_id_checksum(digits13: str) -> bool:
    """Validate 13-digit Thai National ID using official Mod-11 checksum."""
    clean = re.sub(r"\D", "", digits13)
    if len(clean) != 13:
        return False
    total = sum(int(clean[i]) * (13 - i) for i in range(12))
    expected = (11 - (total % 11)) % 10
    return int(clean[12]) == expected


def mask_document_number(doc_num: str, doc_type: str = "THAI_ID") -> str:
    """Mask sensitive ID/Passport numbers for PDPA-safe storage & logging."""
    clean = re.sub(r"[\s\-]", "", doc_num or "")
    if not clean:
        return ""
    if doc_type == "THAI_ID" and len(clean) == 13:
        return f"{clean[0]}-{clean[1:5]}-XXXXX-{clean[10:12]}-{clean[12]}"
    if len(clean) <= 4:
        return "*" * len(clean)
    return f"{clean[:2]}{'*' * (len(clean) - 4)}{clean[-2:]}"


def icao_check_digit(field: str) -> int:
    """Compute ICAO 9303 7-3-1 weighted check digit."""
    weights = (7, 3, 1)
    total = 0
    for idx, ch in enumerate(field):
        val = _ICAO_CHAR_VALUES.get(ch.upper(), 0)
        total += val * weights[idx % 3]
    return total % 10


def _mrz_date_to_iso(yymmdd: str, *, is_expiry: bool = False) -> Optional[str]:
    if len(yymmdd) != 6 or not yymmdd.isdigit():
        return None
    yy = int(yymmdd[0:2])
    mm = int(yymmdd[2:4])
    dd = int(yymmdd[4:6])
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return None
    century = 2000 if is_expiry or yy <= 29 else 1900
    return f"{century + yy:04d}-{mm:02d}-{dd:02d}"


def parse_passport_mrz(text: str) -> Optional[dict[str, Any]]:
    """Parse ICAO 9303 TD3 2-line (44-char) Passport MRZ from OCR text."""
    lines = [re.sub(r"\s+", "", ln).upper() for ln in (text or "").splitlines() if ln.strip()]
    line1: Optional[str] = None
    line2: Optional[str] = None

    for idx, ln in enumerate(lines):
        m1 = _MRZ_LINE1_RE.search(ln)
        if m1:
            line1 = m1.group(0)
            if idx + 1 < len(lines):
                m2 = _MRZ_LINE2_RE.search(lines[idx + 1])
                if m2:
                    line2 = m2.group(0)
                    break
        m2_any = _MRZ_LINE2_RE.search(ln)
        if m2_any and line1 and not line2:
            line2 = m2_any.group(0)
            break

    if not line1 or not line2:
        return None

    issuing_country = line1[2:5].replace("<", "")
    name_raw = line1[5:44]
    if "<<" in name_raw:
        surname_raw, given_raw = name_raw.split("<<", 1)
    else:
        surname_raw, given_raw = name_raw, ""
    surname = surname_raw.replace("<", " ").strip()
    given_names = given_raw.replace("<", " ").strip()
    full_name = " ".join(part for part in (given_names, surname) if part).strip()

    doc_raw = line2[0:9]
    doc_check = line2[9]
    nationality = line2[10:13].replace("<", "")
    dob_raw = line2[13:19]
    dob_check = line2[19]
    sex = line2[20].replace("<", "") or None
    exp_raw = line2[21:27]
    exp_check = line2[27]

    doc_valid = doc_check.isdigit() and icao_check_digit(doc_raw) == int(doc_check)
    dob_valid = dob_check.isdigit() and icao_check_digit(dob_raw) == int(dob_check)
    exp_valid = exp_check.isdigit() and icao_check_digit(exp_raw) == int(exp_check)

    doc_num = doc_raw.replace("<", "")
    return {
        "documentType": "PASSPORT",
        "documentNumberMasked": mask_document_number(doc_num, "PASSPORT"),
        "fullName": full_name or None,
        "surname": surname or None,
        "givenNames": given_names or None,
        "issuingCountry": issuing_country or None,
        "nationality": nationality or None,
        "dateOfBirth": _mrz_date_to_iso(dob_raw, is_expiry=False),
        "expiryDate": _mrz_date_to_iso(exp_raw, is_expiry=True),
        "sex": sex,
        "checksumValid": bool(doc_valid and dob_valid and exp_valid),
        "checks": {
            "documentNumber": doc_valid,
            "dateOfBirth": dob_valid,
            "expiryDate": exp_valid,
        },
    }


def parse_thai_id_text(text: str) -> Optional[dict[str, Any]]:
    """Extract Thai National ID fields from OCR text."""
    raw = text or ""
    match = _THAI_ID_RE.search(raw)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    if len(digits) != 13:
        return None

    checksum_valid = validate_thai_id_checksum(digits)
    name_match = re.search(
        r"(?:Name)\s+(?:(?:Mr\.|Mrs\.|Miss|Ms\.)\s+)?([A-Za-z][A-Za-z\.\- ]{1,60})",
        raw,
        re.IGNORECASE,
    )
    last_match = re.search(
        r"Last\s*name\s+([A-Za-z][A-Za-z\- ]{1,60})",
        raw,
        re.IGNORECASE,
    )
    thai_name_match = re.search(
        r"(?:ชื่อตัวและชื่อสกุล|ชื่อ)\s*[:\-]?\s*([ก-๙ ]{3,80})",
        raw,
    )
    dob_match = re.search(
        r"(?:Date\s*of\s*Birth|DOB)\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4}|\d{4}-\d{2}-\d{2})",
        raw,
        re.IGNORECASE,
    )
    exp_match = re.search(
        r"(?:Date\s*of\s*Expiry|Expiry)\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4}|\d{4}-\d{2}-\d{2})",
        raw,
        re.IGNORECASE,
    )

    eng_parts = []
    if name_match:
        eng_parts.append(name_match.group(1).strip())
    if last_match:
        eng_parts.append(last_match.group(1).strip())
    full_name = " ".join(eng_parts).strip() or (
        thai_name_match.group(1).strip() if thai_name_match else None
    )

    return {
        "documentType": "THAI_ID",
        "documentNumberMasked": mask_document_number(digits, "THAI_ID"),
        "fullName": full_name,
        "nationality": "THA",
        "issuingCountry": "THA",
        "dateOfBirth": dob_match.group(1).strip() if dob_match else None,
        "expiryDate": exp_match.group(1).strip() if exp_match else None,
        "checksumValid": checksum_valid,
    }


def parse_identity_document_text(
    text: str, document_type: str = "AUTO"
) -> dict[str, Any]:
    """Parse raw OCR text into Thai ID or Passport MRZ structured visitor fields."""
    mode = (document_type or "AUTO").strip().upper()
    if mode not in {"AUTO", "THAI_ID", "PASSPORT"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="documentType must be AUTO, THAI_ID, or PASSPORT",
        )

    if mode in {"AUTO", "PASSPORT"}:
        mrz = parse_passport_mrz(text)
        if mrz is not None:
            return mrz
    if mode in {"AUTO", "THAI_ID"}:
        thai = parse_thai_id_text(text)
        if thai is not None:
            return thai

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Could not detect valid Thai ID or Passport MRZ fields from document",
    )


def _run_local_tesseract(image_bytes: bytes) -> str:
    try:
        import pytesseract  # type: ignore[import-untyped]
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local OCR engine (pytesseract/Pillow) is not installed; supply ocrText or enable OCR worker",
        ) from exc

    img = Image.open(io.BytesIO(image_bytes))
    return str(pytesseract.image_to_string(img, lang="eng+tha") or "")


async def extract_document_from_image(
    *,
    image_bytes: Optional[bytes] = None,
    ocr_text: Optional[str] = None,
    document_type: str = "AUTO",
) -> dict[str, Any]:
    """Extract and validate Thai ID or Passport MRZ fields from image bytes or OCR text."""
    text = (ocr_text or "").strip()
    if not text:
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either document image file or ocrText is required",
            )
        text = await asyncio.to_thread(_run_local_tesseract, image_bytes)

    parsed = parse_identity_document_text(text, document_type=document_type)
    return parsed
