#!/bin/bash
# Run pgvector concurrent bench inside dpu-api (has DB driver).
# Args: mode(read|rw) clients queries_per_client company_id member_id write_every
set -euo pipefail
MODE="${1:?read|rw}"
CLIENTS="${2:?}"
QPC="${3:?}"
COMPANY_ID="${4:?}"
SOURCE_MEMBER="${5:?}"
WRITE_EVERY="${6:-10}"
PW="${DPU_SUDO_PW:-}"

printf '%s\n' "$PW" | sudo -S -p '' -v

# Copy bench script into container and run
sudo -n docker exec -i dpu-api python - "$MODE" "$CLIENTS" "$QPC" "$COMPANY_ID" "$SOURCE_MEMBER" "$WRITE_EVERY" <<'PY'
import asyncio, json, os, sys, time, uuid
from statistics import mean

mode, clients_s, qpc_s, company_id, source_member, write_every_s = sys.argv[1:7]
clients = int(clients_s)
qpc = int(qpc_s)
write_every = int(write_every_s)

import asyncpg

url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

SEARCH_SQL = """
SET LOCAL hnsw.ef_search = 40;
SELECT fe."faceEncodingId"::text
FROM face_encoding fe
JOIN company_employee ce ON ce."memberId" = fe."memberId"
WHERE ce."companyId" = $1::uuid AND ce.deleted_at IS NULL
ORDER BY fe.embedding <=> $2::vector
LIMIT 1
"""

async def get_probe(conn):
    row = await conn.fetchrow(
        'SELECT embedding::text AS e FROM face_encoding WHERE "memberId"=$1::uuid LIMIT 1',
        source_member,
    )
    if not row:
        raise SystemExit("no probe embedding")
    return row["e"]

async def search_once(pool, company_id, emb):
    t0 = time.perf_counter()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL hnsw.ef_search = 40")
            await conn.fetchval(
                """
                SELECT fe."faceEncodingId"::text
                FROM face_encoding fe
                JOIN company_employee ce ON ce."memberId" = fe."memberId"
                WHERE ce."companyId" = $1::uuid AND ce.deleted_at IS NULL
                ORDER BY fe.embedding <=> $2::vector
                LIMIT 1
                """,
                company_id,
                emb,
            )
    return (time.perf_counter() - t0) * 1000

async def write_once(pool, company_id, emb):
    """Insert a tiny tagged member+encoding then delete (churn)."""
    tag = "capvec_rw_"
    mid = str(uuid.uuid4())
    async with pool.acquire() as conn:
        async with conn.transaction():
            pos = await conn.fetchrow(
                """
                SELECT ce."positionId", ce."departmentId", ce."empType", ce."companyRoleType"
                FROM company_employee ce
                WHERE ce."companyId"=$1::uuid AND ce.deleted_at IS NULL LIMIT 1
                """,
                company_id,
            )
            await conn.execute(
                """
                INSERT INTO member ("memberId", username, "passwordHash", email, role, status,
                  "must_change_password", "failed_login_count", "createdAt", "updatedAt")
                VALUES ($1::uuid, $2, $3, $4, 'MEMBER'::roletype, 'ENABLE'::statustype,
                  false, 0, now(), now())
                """,
                mid,
                f"{tag}{mid[:8]}",
                "$2b$12$rw.placeholder.hash.value.xxxxxxxxxxxx",
                f"{tag}{mid[:8]}@capvec.invalid",
            )
            await conn.execute(
                """
                INSERT INTO company_employee (
                  "company_employeeId", "memberId", "companyId", "positionId", "departmentId",
                  "employeeId", "empType", "companyRoleType", salary, "createdAt")
                VALUES (gen_random_uuid(), $1::uuid, $2::uuid, $3, $4, 'RW', $5, $6, 0, now())
                """,
                mid,
                company_id,
                pos["positionId"],
                pos["departmentId"],
                pos["empType"],
                pos["companyRoleType"],
            )
            await conn.execute(
                """
                INSERT INTO face_encoding ("faceEncodingId", "memberId", embedding, "createdAt")
                VALUES (gen_random_uuid(), $1::uuid, $2::vector, now())
                """,
                mid,
                emb,
            )
            await conn.execute('DELETE FROM face_encoding WHERE "memberId"=$1::uuid', mid)
            await conn.execute('DELETE FROM company_employee WHERE "memberId"=$1::uuid', mid)
            await conn.execute('DELETE FROM member WHERE "memberId"=$1::uuid', mid)

async def worker(pool, company_id, emb, qpc, do_write, write_every, latencies, lock_waits, errors):
    for i in range(qpc):
        try:
            if do_write and write_every > 0 and (i % write_every == 0):
                await write_once(pool, company_id, emb)
            ms = await search_once(pool, company_id, emb)
            latencies.append(ms)
        except Exception as e:  # noqa: BLE001
            errors.append(type(e).__name__)

async def main():
    pool = await asyncpg.create_pool(url, min_size=2, max_size=min(32, max(4, clients)))
    try:
        async with pool.acquire() as conn:
            emb = await get_probe(conn)
            locks_before = await conn.fetchval(
                "SELECT count(*) FROM pg_locks WHERE granted = false"
            )
        latencies = []
        errors = []
        t0 = time.perf_counter()
        do_write = mode == "rw"
        await asyncio.gather(
            *[
                worker(pool, company_id, emb, qpc, do_write, write_every, latencies, [], errors)
                for _ in range(clients)
            ]
        )
        elapsed = time.perf_counter() - t0
        async with pool.acquire() as conn:
            locks_after = await conn.fetchval(
                "SELECT count(*) FROM pg_locks WHERE granted = false"
            )
            gallery = await conn.fetchval(
                """
                SELECT count(*) FROM face_encoding fe
                JOIN company_employee ce ON ce."memberId"=fe."memberId"
                WHERE ce."companyId"=$1::uuid AND ce.deleted_at IS NULL
                """,
                company_id,
            )
    finally:
        await pool.close()

    latencies.sort()
    def p(pct):
        if not latencies:
            return None
        idx = min(len(latencies) - 1, max(0, int(round((pct / 100) * (len(latencies) - 1)))))
        return round(latencies[idx], 2)

    print(json.dumps({
        "mode": mode,
        "clients": clients,
        "queries_per_client": qpc,
        "total_searches": len(latencies),
        "errors": len(errors),
        "error_samples": errors[:5],
        "elapsed_s": round(elapsed, 2),
        "qps": round(len(latencies) / elapsed, 1) if elapsed else 0,
        "p50_ms": p(50),
        "p95_ms": p(95),
        "p99_ms": p(99),
        "avg_ms": round(mean(latencies), 2) if latencies else None,
        "locks_not_granted_before": locks_before,
        "locks_not_granted_after": locks_after,
        "gallery_company": gallery,
    }))

asyncio.run(main())
PY
