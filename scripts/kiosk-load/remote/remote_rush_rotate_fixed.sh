#!/bin/bash
# Prepare/cleanup rotated members for rush capacity (uses dpu DB user).
set -euo pipefail
ACTION="${1:?prepare|cleanup}"
N="${2:-300}"
COMPANY_ID="${3:?}"
SOURCE_MEMBER="${4:?}"
TAG="${5:-caprush_rot_}"
PW="${DPU_SUDO_PW:-}"

# Cache sudo so later docker exec -i does not mix password with SQL stdin
printf '%s\n' "$PW" | sudo -S -p '' -v
sudo_docker() { sudo -n docker "$@"; }

DB_CTR=dpu-db
URL=$(sudo_docker exec dpu-api printenv DATABASE_URL 2>/dev/null || true)
DB_USER=dpu; DB_NAME=dpu; DB_PASS=dpu_secret
if [ -n "$URL" ]; then
  DB_USER=$(echo "$URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
  DB_PASS=$(echo "$URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
  DB_NAME=$(echo "$URL" | sed -n 's|.*/\([^/?]*\).*|\1|p')
fi
export PGPASSWORD="$DB_PASS"

psql_q() {
  sudo_docker exec -e PGPASSWORD="$PGPASSWORD" -i "$DB_CTR" \
    psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 "$@"
}

cleanup() {
  psql_q <<SQL
DELETE FROM face_encoding WHERE "memberId" IN (SELECT "memberId" FROM member WHERE username LIKE '${TAG}%');
DELETE FROM company_employee WHERE "memberId" IN (SELECT "memberId" FROM member WHERE username LIKE '${TAG}%');
DELETE FROM member WHERE username LIKE '${TAG}%';
SQL
  echo -n "remaining="; psql_q -tAc "SELECT count(*) FROM member WHERE username LIKE '${TAG}%';"
}

case "$ACTION" in
  cleanup) cleanup ;;
  prepare)
    cleanup
    psql_q <<SQL
DO \$\$
DECLARE
  src_pos uuid; src_dept uuid; src_emb vector(512);
  src_et emptype; src_crt companyroletype;
BEGIN
  SELECT ce."positionId", ce."departmentId", ce."empType", ce."companyRoleType"
    INTO src_pos, src_dept, src_et, src_crt
    FROM company_employee ce
   WHERE ce."companyId" = '${COMPANY_ID}'::uuid AND ce.deleted_at IS NULL LIMIT 1;
  IF src_pos IS NULL THEN RAISE EXCEPTION 'no employee for company'; END IF;
  SELECT fe.embedding INTO src_emb FROM face_encoding fe
   WHERE fe."memberId" = '${SOURCE_MEMBER}'::uuid LIMIT 1;
  IF src_emb IS NULL THEN RAISE EXCEPTION 'no source embedding'; END IF;

  INSERT INTO member ("memberId", username, "passwordHash", email, role, status,
    "must_change_password", "failed_login_count", "createdAt", "updatedAt")
  SELECT gen_random_uuid(),
    '${TAG}' || g.i::text || '_' || substr(md5(random()::text),1,6),
    '\$2b\$12\$rush.rotate.placeholder.hash.value.xx',
    '${TAG}' || g.i::text || '@caprush.invalid',
    'MEMBER'::roletype, 'ENABLE'::statustype, false, 0, now(), now()
  FROM generate_series(1, ${N}) g(i);

  INSERT INTO company_employee (
    "company_employeeId", "memberId", "companyId", "positionId", "departmentId",
    "employeeId", "empType", "companyRoleType", salary, "createdAt")
  SELECT gen_random_uuid(), m."memberId", '${COMPANY_ID}'::uuid, src_pos, src_dept,
    'ROT', src_et, src_crt, 0, now()
  FROM member m WHERE m.username LIKE '${TAG}%';

  INSERT INTO face_encoding ("faceEncodingId", "memberId", embedding, "createdAt")
  SELECT gen_random_uuid(), m."memberId", src_emb, now()
  FROM member m WHERE m.username LIKE '${TAG}%';
END \$\$;
SQL
    echo -n "rotated="; psql_q -tAc "SELECT count(*) FROM member WHERE username LIKE '${TAG}%';"
    ;;
  *) echo bad; exit 2;;
esac
