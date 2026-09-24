#!/usr/bin/env python3
"""
Migrate DPU face_encoding rows + enrolled_images to Face Core.

Does NOT delete local face_encoding rows — safe to re-run (skips mapped IDs).

Usage (from API-Fast/):
  python scripts/migrate_faces_to_face_core.py --dry-run
  python scripts/migrate_faces_to_face_core.py
  python scripts/migrate_faces_to_face_core.py --mapping-out migration_mapping.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Register all ORM modules so string relationships resolve.
from src.models import (  # noqa: E402,F401
    company,
    company_employee,
    company_location,
    department,
    employee_timestamp,
    face_encoding,
    member,
    position,
    system_setting,
)
from src.models.face_encoding import FaceEncoding  # noqa: E402
from src.models.company_employee import CompanyEmployee  # noqa: E402

ENROLLED_DIR = Path(os.environ.get("ENROLLED_DIR", "./enrolled_images"))
DEFAULT_MAPPING = Path("migration_face_core_mapping.json")


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise SystemExit("DATABASE_URL is required")
    return url


def _face_core_config() -> tuple[str, str]:
    base = os.environ.get("FACE_CORE_URL", "http://localhost:8081").rstrip("/")
    key = os.environ.get("FACE_CORE_API_KEY", "")
    if not key:
        raise SystemExit("FACE_CORE_API_KEY is required")
    return base, key


async def _ensure_company(client: httpx.AsyncClient, base: str, key: str, code: str) -> None:
    r = await client.put(
        f"{base}/v1/companies/{code}",
        headers={"Authorization": f"Bearer {key}"},
    )
    r.raise_for_status()


async def _enroll(
    client: httpx.AsyncClient,
    base: str,
    key: str,
    company_code: str,
    subject_id: str,
    image_path: Path,
) -> dict:
    with image_path.open("rb") as fh:
        r = await client.post(
            f"{base}/v1/companies/{company_code}/subjects/{subject_id}/faces",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (image_path.name, fh, "image/jpeg")},
        )
    r.raise_for_status()
    return r.json()


async def run_migration(*, dry_run: bool, mapping_out: Path) -> None:
    base, key = _face_core_config()
    database_url = _database_url()

    existing: Dict[str, str] = {}
    if mapping_out.exists():
        existing = json.loads(mapping_out.read_text(encoding="utf-8"))

    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        enc_result = await db.execute(select(FaceEncoding))
        encodings = list(enc_result.scalars().all())

        member_companies: Dict[UUID, Set[UUID]] = defaultdict(set)
        ce_result = await db.execute(select(CompanyEmployee.memberId, CompanyEmployee.companyId))
        for member_id, company_id in ce_result.all():
            member_companies[member_id].add(company_id)

    migrated = dict(existing)
    skipped = 0
    errors: List[str] = []

    timeout = httpx.Timeout(120.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for enc in encodings:
            old_id = str(enc.faceEncodingId)
            if old_id in migrated:
                skipped += 1
                continue

            image_path = ENROLLED_DIR / f"{old_id}.jpg"
            if not image_path.is_file():
                errors.append(f"{old_id}: missing image {image_path}")
                continue

            companies = member_companies.get(enc.memberId) or set()
            if not companies:
                errors.append(f"{old_id}: member {enc.memberId} has no company_employee row")
                continue

            subject_id = str(enc.memberId)
            company_code = str(next(iter(companies)))

            print(f"{'[dry-run] ' if dry_run else ''}migrate {old_id} → company={company_code} subject={subject_id}")
            if dry_run:
                migrated[old_id] = f"dry-run-{old_id}"
                continue

            try:
                await _ensure_company(client, base, key, company_code)
                for cid in companies:
                    await _ensure_company(client, base, key, str(cid))
                    result = await _enroll(
                        client, base, key, str(cid), subject_id, image_path
                    )
                    if str(cid) == company_code:
                        migrated[old_id] = result.get("faceId", "")
            except httpx.HTTPStatusError as exc:
                errors.append(f"{old_id}: HTTP {exc.response.status_code} {exc.response.text[:200]}")
            except Exception as exc:
                errors.append(f"{old_id}: {exc}")

    if not dry_run:
        mapping_out.write_text(json.dumps(migrated, indent=2), encoding="utf-8")

    print(f"Done. total={len(encodings)} migrated={len(migrated)} skipped={skipped} errors={len(errors)}")
    for err in errors[:20]:
        print(f"  ERROR: {err}")
    if len(errors) > 20:
        print(f"  ... and {len(errors) - 20} more")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate DPU faces to Face Core")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without calling Face Core")
    parser.add_argument(
        "--mapping-out",
        type=Path,
        default=DEFAULT_MAPPING,
        help="JSON file mapping old faceEncodingId → new faceId",
    )
    args = parser.parse_args()
    asyncio.run(run_migration(dry_run=args.dry_run, mapping_out=args.mapping_out))


if __name__ == "__main__":
    main()
