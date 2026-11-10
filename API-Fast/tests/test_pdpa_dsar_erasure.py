"""D4 smoke: DSAR export + erasure of punch photos / encodings / incident snapshots."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.config.database import async_session, engine  # noqa: E402
from src.models.company import Company  # noqa: E402
from src.models.company_employee import CompanyEmployee, CompanyRoleType, EmpType  # noqa: E402
from src.models.department import Department  # noqa: E402
from src.models.employee_timestamp import EmployeeTimestamp, TimestampType  # noqa: E402
from src.models.face_encoding import FACE_EMBEDDING_DIM, FaceEncoding  # noqa: E402
from src.models.member import Member, RoleType, StatusType  # noqa: E402
from src.models.position import Position  # noqa: E402
from src.models.sentinel import SentinelIncidentLog  # noqa: E402
from src.services import pdpa_service  # noqa: E402
from src.services.storage_service import ROOTS, ensure_dirs  # noqa: E402

db_test = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def _fresh_pool():
    await engine.dispose(close=False)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="module")
async def pdpa_fx():
    """Minimal company + member with a punch photo, encoding, and incident snapshot."""
    ensure_dirs()
    tag = uuid.uuid4().hex[:8]
    cid = uuid.uuid4()
    mid = uuid.uuid4()
    emp_id = uuid.uuid4()
    dep_id = uuid.uuid4()
    pos_id = uuid.uuid4()
    photo_name = f"pdpa-punch-{tag}.jpg"
    snap_name = f"pdpa-snap-{tag}.jpg"
    (ROOTS["uploaded_images"] / photo_name).write_bytes(b"fake-jpeg-punch")
    (ROOTS["uploaded_images"] / snap_name).write_bytes(b"fake-jpeg-snap")

    async with async_session() as db:
        db.add(
            Company(
                companyId=cid,
                companyName=f"PDPA Co {tag}",
                companyCode=f"PDPA{tag}",
                companyInfo="pdpa",
                address="n/a",
                latitude=13.7,
                longitude=100.5,
                picture="",
            )
        )
        m = Member(
            memberId=mid,
            username=f"pdpa_{tag}",
            email=f"pdpa_{tag}@example.com",
            firstName="Ada",
            lastName="Lovelace",
            role=RoleType.MEMBER,
            status=StatusType.ENABLE,
            biometricConsentAt=datetime.now(timezone.utc),
            biometricConsentVersion="1.0",
            biometricConsentText="test consent",
        )
        m.hash_password("Passw0rd!xyz")
        db.add(m)
        db.add(
            Department(
                departmentId=dep_id,
                companyId=cid,
                thName="IT",
                engName="IT",
            )
        )
        db.add(
            Position(
                positionId=pos_id,
                companyId=cid,
                thName="Dev",
                engName="Dev",
            )
        )
        await db.flush()
        db.add(
            CompanyEmployee(
                company_employeeId=emp_id,
                memberId=mid,
                companyId=cid,
                departmentId=dep_id,
                positionId=pos_id,
                employeeId=f"E-{tag}",
                empType=EmpType.PERMONTH,
                companyRoleType=CompanyRoleType.EMP,
            )
        )
        db.add(
            FaceEncoding(
                faceEncodingId=uuid.uuid4(),
                memberId=mid,
                companyId=cid,
                embedding=[0.0] * FACE_EMBEDDING_DIM,
            )
        )
        db.add(
            EmployeeTimestamp(
                timestampId=uuid.uuid4(),
                company_employeeId=emp_id,
                companyId=cid,
                timestampType=TimestampType.CHECK_IN,
                photoTimestamp=photo_name,
            )
        )
        db.add(
            SentinelIncidentLog(
                incidentId=uuid.uuid4(),
                companyId=cid,
                eventType="TEST",
                severity="INFO",
                memberId=mid,
                subjectName="Ada Lovelace",
                snapshotUrl=f"/images/{snap_name}",
            )
        )
        await db.commit()

    yield {
        "companyId": cid,
        "memberId": mid,
        "photo": photo_name,
        "snap": snap_name,
    }

    async with async_session() as db:
        await db.execute(FaceEncoding.__table__.delete().where(FaceEncoding.memberId == mid))
        await db.execute(
            EmployeeTimestamp.__table__.delete().where(EmployeeTimestamp.companyId == cid)
        )
        await db.execute(
            SentinelIncidentLog.__table__.delete().where(SentinelIncidentLog.companyId == cid)
        )
        await db.execute(
            CompanyEmployee.__table__.delete().where(CompanyEmployee.companyId == cid)
        )
        await db.execute(Position.__table__.delete().where(Position.companyId == cid))
        await db.execute(Department.__table__.delete().where(Department.companyId == cid))
        await db.execute(Member.__table__.delete().where(Member.memberId == mid))
        await db.execute(Company.__table__.delete().where(Company.companyId == cid))
        await db.commit()
    for name in (photo_name, snap_name):
        p = ROOTS["uploaded_images"] / name
        if p.exists():
            p.unlink()


@db_test
async def test_dsar_export_includes_member_and_media_refs(pdpa_fx):
    async with async_session() as db:
        payload = await pdpa_service.build_dsar_export(
            db, pdpa_fx["companyId"], pdpa_fx["memberId"]
        )
    assert payload["member"]["firstName"] == "Ada"
    assert payload["member"]["biometricConsentVersion"] == "1.0"
    assert len(payload["faceEncodings"]) == 1
    assert payload["faceEncodings"][0]["embeddingPresent"] is True
    assert any(t["photoTimestamp"] == pdpa_fx["photo"] for t in payload["timestamps"])
    assert any(pdpa_fx["snap"] in (i["snapshotUrl"] or "") for i in payload["incidents"])


@db_test
async def test_erasure_removes_photos_encodings_and_snapshots(pdpa_fx):
    async with async_session() as db:
        result = await pdpa_service.erase_member_personal_data(
            db, pdpa_fx["companyId"], pdpa_fx["memberId"]
        )
    assert result["deletedEncodings"] >= 1
    assert result["punchPhotosRemoved"] >= 1
    assert result["incidentSnapshotsRemoved"] >= 1
    assert not (ROOTS["uploaded_images"] / pdpa_fx["photo"]).exists()
    assert not (ROOTS["uploaded_images"] / pdpa_fx["snap"]).exists()

    async with async_session() as db:
        encs = (
            await db.execute(
                select(FaceEncoding).where(FaceEncoding.memberId == pdpa_fx["memberId"])
            )
        ).scalars().all()
        assert encs == []
        member = await db.get(Member, pdpa_fx["memberId"])
        assert member.biometricConsentAt is None
        assert member.biometricConsentVersion is None
        ts = (
            await db.execute(
                select(EmployeeTimestamp).where(
                    EmployeeTimestamp.companyId == pdpa_fx["companyId"]
                )
            )
        ).scalars().all()
        assert all(t.photoTimestamp is None for t in ts)


@db_test
async def test_consent_policy_roundtrip():
    tag = uuid.uuid4().hex[:8]
    cid = uuid.uuid4()
    async with async_session() as db:
        db.add(
            Company(
                companyId=cid,
                companyName=f"Consent Co {tag}",
                companyCode=f"CNS{tag}",
                companyInfo="c",
                address="n/a",
                latitude=0,
                longitude=0,
            )
        )
        await db.commit()
        saved = await pdpa_service.put_consent_policy(
            db,
            cid,
            {"version": "2.1", "textTh": "ข้อความ", "textEn": "English text"},
        )
        assert saved["version"] == "2.1"
        got = await pdpa_service.get_consent_policy(db, cid)
        assert got["textEn"] == "English text"
        await db.execute(Company.__table__.delete().where(Company.companyId == cid))
        await db.commit()
