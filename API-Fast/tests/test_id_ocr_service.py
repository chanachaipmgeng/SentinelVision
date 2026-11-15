"""Tests for Thai National ID & ICAO 9303 Passport MRZ OCR parser."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
import pytest

from src.routes.sentinel_routes import ocr_public_visitor_document
from src.services.id_ocr_service import (
    extract_document_from_image,
    parse_identity_document_text,
    validate_thai_id_checksum,
)
from src.services.visitor_invite_service import create_visitor_invite_token


def test_thai_id_parsing_and_mod11_checksum() -> None:
    assert validate_thai_id_checksum("1101700203450") is True
    assert validate_thai_id_checksum("1101700203459") is False

    sample = (
        "Thai National ID Card\n"
        "Identification Number 1-1017-00203-45-0\n"
        "Name Mr. Somchai\n"
        "Last name Jaidee\n"
        "Date of Birth 15 Jan 1990\n"
        "Date of Expiry 14 Jan 2030\n"
    )
    parsed = parse_identity_document_text(sample, document_type="AUTO")
    assert parsed["documentType"] == "THAI_ID"
    assert parsed["documentNumberMasked"] == "1-1017-XXXXX-45-0"
    assert parsed["checksumValid"] is True
    assert parsed["fullName"] == "Somchai Jaidee"
    assert parsed["nationality"] == "THA"
    assert parsed["dateOfBirth"] == "15 Jan 1990"
    assert parsed["expiryDate"] == "14 Jan 2030"


def test_passport_mrz_td3_parsing_and_check_digits() -> None:
    mrz = (
        "P<THASOMCHAI<<JAIDEE<<<<<<<<<<<<<<<<<<<<<<<<\n"
        "AA12345678THA9001158M3012316<<<<<<<<<<<<<<00\n"
    )
    parsed = parse_identity_document_text(mrz, document_type="PASSPORT")
    assert parsed["documentType"] == "PASSPORT"
    assert parsed["documentNumberMasked"] == "AA*****67"
    assert parsed["issuingCountry"] == "THA"
    assert parsed["nationality"] == "THA"
    assert parsed["surname"] == "SOMCHAI"
    assert parsed["givenNames"] == "JAIDEE"
    assert parsed["fullName"] == "JAIDEE SOMCHAI"
    assert parsed["dateOfBirth"] == "1990-01-15"
    assert parsed["expiryDate"] == "2030-12-31"
    assert parsed["sex"] == "M"
    assert parsed["checksumValid"] is True


def test_invalid_ocr_text_and_document_type() -> None:
    with pytest.raises(HTTPException) as exc_bad_type:
        parse_identity_document_text("anything", document_type="DRIVER_LICENSE")
    assert exc_bad_type.value.status_code == 400

    with pytest.raises(HTTPException) as exc_unparsed:
        parse_identity_document_text("No ID or MRZ present here", document_type="AUTO")
    assert exc_unparsed.value.status_code == 422


@pytest.mark.asyncio
async def test_public_visitor_ocr_endpoint_with_invite_token() -> None:
    invite = create_visitor_invite_token(
        company_id=uuid.uuid4(),
        visitor_name="Somchai Jaidee",
        host_name="Reception",
    )
    res = await ocr_public_visitor_document(
        token=invite["inviteToken"],
        file=None,
        ocrText="Identification Number 1-1017-00203-45-0\nName Mr. Somchai\nLast name Jaidee",
        documentType="THAI_ID",
    )
    assert res["ok"] is True
    assert res["document"]["documentType"] == "THAI_ID"
    assert res["document"]["checksumValid"] is True

    with pytest.raises(HTTPException) as exc_bad_tok:
        await extract_document_from_image(image_bytes=None, ocr_text=None)
    assert exc_bad_tok.value.status_code == 400

    with pytest.raises(HTTPException) as exc_unauth:
        await ocr_public_visitor_document(
            token="sv_vis_tampered.bad",
            file=None,
            ocrText="1101700203450",
            documentType="THAI_ID",
        )
    assert exc_unauth.value.status_code == 401
