# Secrets & PII Remediation (Roadmap A2)

Status of the two halves of A2:

| Step | State | Where |
|---|---|---|
| Stop tracking secrets / PII, ignore rules, `.env.example`, externalize Google Maps key | **Done** (PR #3 `chore/a2-untrack-secrets-and-pii`, merged via PR #8) | this repo |
| Purge from git history | **Done 2026-11-07** (see §6) | §2, §6 |
| Rotate `SECRET_KEY`, `POSTGRES_PASSWORD` | **Done 2026-11-07** (see §6) | §4, §6 |
| Rotate Google Maps key, Firebase web config; GitHub cache purge; collaborator re-clone | **Pending — owner actions** (see §6) | §3, §4, §6 |

The Google Maps key and the Firebase web config were published in history until the rewrite and GitHub may still serve the old commits from cache; keep treating them as compromised until §6's remaining actions are done.

---

## 1. Inventory (what was tracked and is now untracked)

Sizes are from the working tree at the time of the PR. Files were removed with `git rm --cached` only — they still exist on disk and are now covered by `.gitignore`.

| Path | Files | Size | Type | Why it must not be in git |
|---|---|---|---|---|
| `API-Fast/.env` | 1 | 316 B | **Secret** | `DATABASE_URL` with a real DB password and a `SECRET_KEY` (a signed JWT reused as HMAC secret) |
| `API-Fast/uploaded_images/*.jpg` | 811 | 63,581,414 B (~63 MB) | **Biometric PII** | Face crops / punch photos of real people (PDPA sensitive data) |
| `API-Fast/uploads/face.jpg`, `ooh-ao.jpg`, `ssss.png` | 3 | 616,866 B | **PII** | Test face photos |
| `API-Fast/_inspect_import.xlsx` | 1 | 7,620 B | Scratch data | Employee-import inspection workbook (3 sheets) — scratch output, not source |
| `ผลโหลดเทส/EXEC-SUMMARY-KIOSK-CAPACITY.html` | 1 | 20,412 B | Build artifact | Load-test result dump in repo root; the curated copy lives in `docs/` |

Edited in place (not untracked):

| Path | Finding | Fix in this PR |
|---|---|---|
| `Web-Manage/src/index.html` (lines 108, 118) | Google Maps browser API key hard-coded twice | Removed; the admin container no longer accepts a Maps key and map widgets use OSM |
| `Web-Manage/src/environments/environment.ts`, `environment.prod.ts` | Firebase web config (`apiKey`, `appId`, `messagingSenderId`, …) | Values blanked (Firebase is not used — `@angular/fire` was removed); block kept as schema placeholder with injection instructions |

Not changed, review separately:

- `docs/screenshots/*.png` (10 files, ~3.2 MB) — user-manual screenshots taken from a live stack. Check for employee names / faces before the history rewrite so they can be purged in the same pass if needed.
- `docs/*.html`, `docs/*.pdf` — curated capacity reports; intentionally kept.
- `.git` pack is ~260 MB; most of it is the 811 face images plus `Web-Manage/src/assets` binaries. Expect a large drop after §2.

New ignore rules (root `.gitignore`): `.env.*` (except `.env.example`), `Web-Manage/src/assets/config.json`, `API-Fast/**/*.{jpg,jpeg,png,webp}`, `API-Fast/*.{xlsx,xls,csv}`, `API-Fast/_inspect_*`, `ผลโหลดเทส/`, `loadtest-results/`, `scripts/kiosk-load/results/`.

---

## 2. History rewrite (`git filter-repo`) — run once, by one person

Prerequisites

1. Freeze pushes: announce a merge freeze, make sure every open PR/MR is merged or its branch is pushed.
2. `pip install git-filter-repo` (or `brew install git-filter-repo`).
3. Work in a **fresh mirror clone**; never run this inside a developer checkout.

```bash
git clone --mirror git@github.com:<org>/SentinelVision.git sv-rewrite.git
cd sv-rewrite.git

# Keep a backup of the original refs (or rely on the forge's old objects for a few days)
git bundle create ../sv-before-rewrite.bundle --all

# Remove every path from the inventory in all commits
git filter-repo --invert-paths \
  --path API-Fast/.env \
  --path API-Fast/uploaded_images \
  --path API-Fast/uploads \
  --path API-Fast/_inspect_import.xlsx \
  --path 'ผลโหลดเทส'

# Scrub the literal secrets wherever else they appear in history (index.html, env files, docs)
cat > ../expressions.txt <<'EOF'
# Google Maps browser keys historically used a fixed 4-letter prefix plus 30+ alnum/_/-.
# Put that regex only in a machine-local expressions file — do not commit the live prefix.
regex:GOOGLE_MAPS_BROWSER_KEY_PATTERN==>REDACTED_GOOGLE_MAPS_KEY
regex:SECRET_KEY=.*==>SECRET_KEY=REDACTED
regex:postgresql\+asyncpg://[^:]+:[^@]+@==>postgresql+asyncpg://REDACTED:REDACTED@
EOF
# Add the Firebase apiKey / appId / messagingSenderId literals from the pre-PR
# environment*.ts to expressions.txt as `literal:<value>==>REDACTED` lines before running.
git filter-repo --replace-text ../expressions.txt

# Sanity: nothing left
git log --all --oneline -- API-Fast/.env | wc -l          # expect 0
git grep -I -l 'GOOGLE_MAPS_API_KEY' $(git rev-list --all) | wc -l  # spot-check; also grep the live Maps key prefix offline
git count-objects -vH                                      # size-pack should drop well below 260 MB

# Push the rewritten history (filter-repo removes the origin remote on purpose)
git remote add origin git@github.com:<org>/SentinelVision.git
git push --force --mirror origin
```

After the push

- On GitHub: Settings → ask support / use the UI to clear cached views and run GC, or at minimum delete and re-create any protected-branch rule that blocked the force push, then re-enable protection.
- Invalidate forks and CI runner caches that still hold old objects (GitLab runner cache, Docker build cache with `COPY . .`).
- Keep `sv-before-rewrite.bundle` offline for 30 days, then delete it.

## 3. Re-clone notice (send to every developer and CI maintainer)

> **SentinelVision history was rewritten on `<date>` to remove committed secrets and face images.**
> Do **not** `git pull`, `merge`, or `rebase` an old checkout — it will re-introduce the purged objects.
>
> 1. Push any unmerged branch to a temporary remote name **before** the freeze ends (or export patches with `git format-patch`).
> 2. Delete the old clone: `rm -rf SentinelVision`.
> 3. `git clone git@github.com:<org>/SentinelVision.git`.
> 4. Re-apply local branches with `git am` / `git cherry-pick` onto the new `main`.
> 5. Recreate local untracked files: `cp .env.example .env`, `cp API-Fast/.env.example API-Fast/.env`, `cp Web-Manage/src/assets/config.example.json Web-Manage/src/assets/config.json`, then fill in **new** (rotated) values.
> 6. CI / deploy hosts that `git pull` in place (`docs/DEPLOY-SERVER.md §8`) must also re-clone.

## 4. Key rotation checklist

Rotate **after** the PR is merged and **before/at** the history rewrite. Order matters: rotate the DB password last because `api` restarts take the kiosk down.

| # | Secret | Where it leaked | Rotation steps | Side effects |
|---|---|---|---|---|
| 1 | `SECRET_KEY` (JWT HMAC) | `API-Fast/.env` in history | `python -c "import secrets; print(secrets.token_urlsafe(48))"` → set in deploy `.env` (root and/or `API-Fast/.env` for non-Docker runs) → `docker compose up -d api api-gpu1` → confirm `/ready` | Every access/refresh/**kiosk** token is invalid immediately; re-login all admins, re-issue kiosk tokens (`/hr/kiosk-devices`) and re-pair each kiosk |
| 2 | Google Maps browser API key | `index.html` in history (public bundle too) | Google Cloud Console → APIs & Services → Credentials → **delete the leaked key**. Do not create a replacement in git or `.env`. Compose forces an empty key and admin maps stay on OSM | Admin map widgets use OSM |
| 3 | Firebase web config | `environment*.ts` in history | Firebase console → Project settings → check whether the web app is still needed. App code does not use it: **delete the web app / restrict the API key** (Google Cloud → Credentials → the auto-created "Browser key (auto created by Firebase)") | None for DPU (unused) |
| 4 | `POSTGRES_PASSWORD` / `DATABASE_URL` password | `API-Fast/.env` in history and compose default `dpu_secret` | Generate a strong password → `ALTER USER dpu WITH PASSWORD '<new>';` on the running DB (and the shared `dev-postgres` user if used) → update `POSTGRES_PASSWORD` / `DATABASE_URL` in `.env` → `docker compose up -d api api-gpu1` → verify `/ready` and one check-in | Short API outage during restart; `scripts/backup.sh` must get the new password |
| 5 | Any value in `.env` copied from the leaked file | `SMTP_PASSWORD`, `LINE_CHANNEL_ACCESS_TOKEN`, `WEBHOOK_SIGNING_SECRET`, `FACE_CORE_API_KEY`, `S3_*` | Rotate at the provider if they were ever the same as a value in git | Webhook consumers need the new signing secret |

Evidence to keep in the change ticket: date/time of each rotation, who did it, and the output of the sanity commands in §2.

## 5. Preventing recurrence

- `.gitignore` now blocks `.env*`, face image folders, scratch spreadsheets and load-test dumps; `*.example` files are the only tracked templates.
- Add a secret scanner to CI before merging (`gitleaks detect --redact` in `.gitlab-ci.yml` `lint` stage, or GitHub secret scanning + push protection on the repo).
- Pre-commit hook suggestion: `pre-commit` with `gitleaks` and `check-added-large-files --maxkb=500`.
- Runtime secrets belong in `.env` (Docker) or the orchestrator's secret store, never in `index.html`, `environment*.ts`, or docs.

## 6. Execution log — 2026-11-07

Performed on the owner's workstation after PR #8 (Phase A integration) was merged into `main` with a merge commit (`a3d78344`, rewritten to `878494f6`).

**Backup (keep offline ≥ 30 days, then delete):** `D:\Project\myProject\SentinelVision-backup-20261107.bundle` — full `git clone --mirror` of the pre-rewrite repository (all branches, tags and `refs/pull/*`, ~260 MB, `git bundle verify` OK). It contains the leaked values; do not copy it anywhere shared.

**History rewrite** — `git filter-repo` 2.47 on a fresh mirror clone, single pass, 120 commits rewritten; branches `main`, `DEV` and tags `v1`, `v1.1.0`, `v.1.2.0` force-pushed.

- Paths removed from every commit (`--invert-paths --paths-from-file`): `API-Fast/.env`, `API-Fast/uploaded_images/`, `API-Fast/uploads/`, `API-Fast/_inspect_import.xlsx`, `ผลโหลดเทส/`.
- Literals replaced with `***REMOVED***` (`--replace-text`): the `SECRET_KEY` value and the `DATABASE_URL` password from the historical `API-Fast/.env`; the Google Maps browser key from `Web-Manage/src/index.html`; plus a safety regex for Google Maps browser keys. The Firebase `apiKey` / `appId` / `messagingSenderId` in `environment*.ts` were already masked (`***`) in every historical revision, so nothing to replace. The compose default `dpu_secret` was deliberately **not** rewritten (it is the public example value in `docker-compose.yml` / `.env.example`; the real password was rotated instead).
- Verification on the rewritten mirror: `git log --all -- API-Fast/.env` → 0 commits; purged paths absent from all trees; `git grep` for each literal and for Google Maps browser key patterns over `git rev-list --all` → 0 hits; new `main` tree id identical to the old `main` tree id (`git diff --stat` empty); `DEV` and tags differ only in the purged files. Pack size 260 MB → 221 MB (the remaining bulk is `Web-Manage/src/assets/models/*`).
- Owner checkout reset onto the rewritten history (`fetch --prune`, `reset --hard origin/main`, tags re-fetched, `reflog expire --expire=now --all`, `gc --prune=now --aggressive`); the old `main` object is no longer present locally. Local gitignored `.env` untouched.
- Merged feature branches deleted on origin: `fix/a1-audit-service-imports`, `fix/a7-kiosk-blacklist-exposure`, `chore/a2-untrack-secrets-and-pii`, `fix/a3-kiosk-ws-auth-gating`, `fix/a6-tenant-isolation`, `feat/a5-token-lifecycle-kiosk-pairing`, `feat/a4-real-oidc`, `integration/phase-a`.

**Rotated (values live only in the gitignored root `.env`):**

- `SECRET_KEY` — new 64-char random value. Every pre-existing access/refresh/kiosk token is invalid; admins must log in again and kiosks must be re-paired (`/kiosk/pair`).
- `POSTGRES_PASSWORD` for role `dpu` on the builtin `sentinel-db` container (`ALTER USER dpu WITH PASSWORD …`), new 32-char random value; `DATABASE_URL` is derived from it by `docker-compose.yml`. Verified: old default password rejected over the network, new one accepted, `api` recreated, `/health` and `/ready` 200, login works, pre-rotation token → 401, startup DDL clean.

**Still to do (owner):**

1. Google Maps key — Google Cloud Console → Credentials: **delete the leaked key**. Do not put a replacement in git or `.env`. Compose keeps the key empty so admin maps stay on OSM.
2. Firebase web app — Firebase console / Google Cloud Credentials: delete the web app or restrict/regenerate its browser key (unused by DPU).
3. GitHub — the old commits are still reachable through `refs/pull/1..8/head` and GitHub's cache (e.g. `/commit/a3d78344`, PR diff views). Ask GitHub Support to purge unreachable objects / dereference the pull-request refs for `chanachaipmgeng/SentinelVision`, then turn on secret scanning + push protection.
4. Every other clone (CI runners, deploy hosts per `docs/DEPLOY-SERVER.md`, developers, Docker build caches) must be **re-cloned, not pulled** — see §3. The sibling `dpu-project` checkout (Bitbucket remote) carries the same pre-A2 history and the old DB password in its `.env`; if that stack is started against the shared `dpu-project_pgdata` volume, update its `POSTGRES_PASSWORD` first.
5. `scripts/backup.sh` and any monitoring that used the old DB password need the new value.
