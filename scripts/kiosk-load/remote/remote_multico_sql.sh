#!/bin/bash
set -euo pipefail
ACTION="${1:?insert|delete|list}"
N="${2:-20}"
SOURCE_COMPANY="${3:?}"
SOURCE_MEMBER="${4:?}"
TAG_PREFIX="${5:-capco_sweep_}"
OUT_JSON="${6:-/tmp/capco_companies.json}"
LOAD_MEMBER="${7:-$SOURCE_MEMBER}"
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

case "$ACTION" in
  delete)
    echo "Deleting tagged multi-co ${TAG_PREFIX}* ..."
    psql_q <<SQL
DELETE FROM face_encoding WHERE "memberId" IN (
  SELECT "memberId" FROM member WHERE username LIKE '${TAG_PREFIX}%');
DELETE FROM company_employee WHERE "companyId" IN (
  SELECT "companyId" FROM company WHERE "companyName" LIKE '${TAG_PREFIX}%');
DELETE FROM company_employee WHERE "memberId" IN (
  SELECT "memberId" FROM member WHERE username LIKE '${TAG_PREFIX}%');
DELETE FROM "position" WHERE "companyId" IN (
  SELECT "companyId" FROM company WHERE "companyName" LIKE '${TAG_PREFIX}%');
DELETE FROM department WHERE "companyId" IN (
  SELECT "companyId" FROM company WHERE "companyName" LIKE '${TAG_PREFIX}%');
DELETE FROM member WHERE username LIKE '${TAG_PREFIX}%';
DELETE FROM company WHERE "companyName" LIKE '${TAG_PREFIX}%';
SQL
    echo deleted_ok
    ;;
  insert)
    echo "Creating $N companies (load member=$LOAD_MEMBER) ..."
    psql_q <<SQL
DO \$\$
DECLARE
  i int; cid uuid; mid uuid; did uuid; pid uuid;
  emb vector(512); cname text; uname text;
  st_co publictype; et emptype; crt_emp companyroletype; crt_admin companyroletype;
BEGIN
  SELECT c.status INTO st_co FROM company c LIMIT 1;
  SELECT ce."empType" INTO et FROM company_employee ce LIMIT 1;
  crt_emp := 'EMP'::companyroletype;
  crt_admin := 'ADMIN_COMPANY'::companyroletype;
  SELECT fe.embedding INTO emb FROM face_encoding fe
   WHERE fe."memberId" = '$SOURCE_MEMBER'::uuid LIMIT 1;
  IF emb IS NULL THEN RAISE EXCEPTION 'missing source embedding'; END IF;

  FOR i IN 1..$N LOOP
    cid := gen_random_uuid(); mid := gen_random_uuid();
    did := gen_random_uuid(); pid := gen_random_uuid();
    cname := '${TAG_PREFIX}' || lpad(i::text, 3, '0');
    uname := '${TAG_PREFIX}m' || lpad(i::text, 3, '0');

    INSERT INTO company (
      "companyId", "companyName", "companyCode", "companyInfo", address,
      latitude, longitude, status, "createdAt", "updatedAt"
    ) VALUES (
      cid, cname, cname, 'capacity multi-co', 'cap address',
      13.8772, 100.5115, st_co, now(), now()
    );
    INSERT INTO department ("departmentId", "thName", "engName", "companyId", "createdAt")
    VALUES (did, 'แผนกทดสอบ', 'CapDept', cid, now());
    INSERT INTO "position" ("positionId", "thName", "engName", "companyId", "createdAt")
    VALUES (pid, 'ตำแหน่งทดสอบ', 'CapPos', cid, now());
    INSERT INTO member (
      "memberId", username, "passwordHash", email, role, status,
      "must_change_password", "failed_login_count", "createdAt", "updatedAt"
    ) VALUES (
      mid, uname,
      '\$2b\$12\$multico.sweep.placeholder.hash.value.xx',
      uname || '@capco.invalid',
      'MEMBER'::roletype, 'ENABLE'::statustype, false, 0, now(), now()
    );
    INSERT INTO company_employee (
      "company_employeeId", "memberId", "companyId", "positionId", "departmentId",
      "employeeId", "empType", "companyRoleType", salary, "createdAt"
    ) VALUES (
      gen_random_uuid(), mid, cid, pid, did, 'CO' || i::text, et, crt_emp, 0, now()
    );
    INSERT INTO company_employee (
      "company_employeeId", "memberId", "companyId", "positionId", "departmentId",
      "employeeId", "empType", "companyRoleType", salary, "createdAt"
    ) VALUES (
      gen_random_uuid(), '$LOAD_MEMBER'::uuid, cid, pid, did, 'LOAD', et, crt_admin, 0, now()
    );
    INSERT INTO face_encoding ("faceEncodingId", "memberId", embedding, "createdAt")
    VALUES (gen_random_uuid(), mid, emb, now());
  END LOOP;
END \$\$;
SQL
    psql_q -tAc "COPY (
      SELECT json_agg(json_build_object(
        'companyId', c.\"companyId\",
        'companyName', c.\"companyName\",
        'memberId', m.\"memberId\",
        'username', m.username
      ))
      FROM company c
      JOIN company_employee ce ON ce.\"companyId\" = c.\"companyId\"
      JOIN member m ON m.\"memberId\" = ce.\"memberId\"
      WHERE c.\"companyName\" LIKE '${TAG_PREFIX}%'
        AND m.username LIKE '${TAG_PREFIX}%'
    ) TO STDOUT" > "$OUT_JSON"
    echo "wrote $OUT_JSON"; wc -c "$OUT_JSON"
    ;;
  list)
    psql_q -tAc "COPY (
      SELECT json_agg(json_build_object(
        'companyId', c.\"companyId\",
        'memberId', m.\"memberId\",
        'companyName', c.\"companyName\"
      ))
      FROM company c
      JOIN company_employee ce ON ce.\"companyId\" = c.\"companyId\"
      JOIN member m ON m.\"memberId\" = ce.\"memberId\"
      WHERE c.\"companyName\" LIKE '${TAG_PREFIX}%'
        AND m.username LIKE '${TAG_PREFIX}%'
    ) TO STDOUT"
    ;;
  *) echo bad; exit 2;;
esac
