#!/bin/bash
set -euo pipefail
ACTION="${1:?insert|delete|count}"
N="${2:-0}"
COMPANY_ID="${3:?}"
SOURCE_MEMBER="${4:?}"
TAG_PREFIX="${5:-capgal_sweep_}"
PW="${DPU_SUDO_PW:-}"

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

count_tagged() {
  psql_q -tAc "SELECT count(*) FROM face_encoding fe
    JOIN member m ON m.\"memberId\" = fe.\"memberId\"
    WHERE m.username LIKE '${TAG_PREFIX}%';"
}

case "$ACTION" in
  count)
    echo -n "gallery_tagged="; count_tagged
    echo -n "gallery_company="; psql_q -tAc "SELECT count(*) FROM face_encoding fe
      JOIN company_employee ce ON ce.\"memberId\" = fe.\"memberId\"
      WHERE ce.\"companyId\" = '$COMPANY_ID' AND ce.deleted_at IS NULL;"
    ;;
  delete)
    echo "Deleting tagged ${TAG_PREFIX}* ..."
    psql_q <<SQL
DELETE FROM face_encoding WHERE "memberId" IN (SELECT "memberId" FROM member WHERE username LIKE '${TAG_PREFIX}%');
DELETE FROM company_employee WHERE "memberId" IN (SELECT "memberId" FROM member WHERE username LIKE '${TAG_PREFIX}%');
DELETE FROM member WHERE username LIKE '${TAG_PREFIX}%';
SQL
    echo -n "remaining_tagged="; count_tagged
    ;;
  insert)
    echo "Inserting $N synthetic gallery rows ..."
    psql_q <<SQL
DO \$\$
DECLARE
  src_pos uuid; src_dept uuid; src_emb vector(512);
  src_role roletype; src_status statustype;
  src_et emptype; src_crt companyroletype;
BEGIN
  SELECT ce."positionId", ce."departmentId", ce."empType", ce."companyRoleType"
    INTO src_pos, src_dept, src_et, src_crt
    FROM company_employee ce
   WHERE ce."companyId" = '$COMPANY_ID'::uuid AND ce.deleted_at IS NULL LIMIT 1;
  IF src_pos IS NULL THEN RAISE EXCEPTION 'no company_employee'; END IF;
  SELECT fe.embedding INTO src_emb FROM face_encoding fe
   WHERE fe."memberId" = '$SOURCE_MEMBER'::uuid LIMIT 1;
  IF src_emb IS NULL THEN RAISE EXCEPTION 'no source embedding'; END IF;
  SELECT m.role, m.status INTO src_role, src_status
    FROM member m WHERE m."memberId" = '$SOURCE_MEMBER'::uuid;

  INSERT INTO member ("memberId", username, "passwordHash", email, role, status,
    "must_change_password", "failed_login_count", "createdAt", "updatedAt")
  SELECT gen_random_uuid(),
    '${TAG_PREFIX}' || g.i::text || '_' || substr(md5(random()::text), 1, 6),
    '\$2b\$12\$gallery.sweep.placeholder.hash.value.xx',
    '${TAG_PREFIX}' || g.i::text || '@capgal.invalid',
    'MEMBER'::roletype, 'ENABLE'::statustype, false, 0, now(), now()
  FROM generate_series(1, $N) AS g(i);

  INSERT INTO company_employee (
    "company_employeeId", "memberId", "companyId", "positionId", "departmentId",
    "employeeId", "empType", "companyRoleType", salary, "createdAt")
  SELECT gen_random_uuid(), m."memberId", '$COMPANY_ID'::uuid, src_pos, src_dept,
    'GAL', src_et, src_crt, 0, now()
  FROM member m WHERE m.username LIKE '${TAG_PREFIX}%'
    AND NOT EXISTS (SELECT 1 FROM company_employee ce WHERE ce."memberId" = m."memberId");

  INSERT INTO face_encoding ("faceEncodingId", "memberId", embedding, "createdAt")
  SELECT gen_random_uuid(), m."memberId", src_emb, now()
  FROM member m WHERE m.username LIKE '${TAG_PREFIX}%'
    AND NOT EXISTS (SELECT 1 FROM face_encoding fe WHERE fe."memberId" = m."memberId");
END \$\$;
SQL
    echo -n "gallery_tagged="; count_tagged
    echo -n "gallery_company="; psql_q -tAc "SELECT count(*) FROM face_encoding fe
      JOIN company_employee ce ON ce.\"memberId\" = fe.\"memberId\"
      WHERE ce.\"companyId\" = '$COMPANY_ID' AND ce.deleted_at IS NULL;"
    ;;
  *) echo unknown; exit 2;;
esac
