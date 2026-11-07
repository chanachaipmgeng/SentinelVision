# Secrets & PII Remediation (Roadmap A2)

Status of the two halves of A2:

| Step | State | Where |
|---|---|---|
| Stop tracking secrets / PII, ignore rules, `.env.example`, externalize Google Maps key | **Done** (PR `chore/a2-untrack-secrets-and-pii`) | this repo |
| Purge from git history + rotate keys | **Pending — needs owner go-ahead** (destructive, every clone must be re-cloned) | §2–§4 below |

Until §2–§4 are executed the leaked values are still readable in history (`git log -p -- API-Fast/.env`) and **must be treated as compromised**.

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
| `Web-Manage/src/index.html` (lines 108, 118) | Google Maps API key `AIza…` hard-coded twice | Removed; SDK is now injected at startup from `assets/config.json` (`src/app/shared/runtime-config.ts`) |
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
regex:AIza[0-9A-Za-z_\-]{30,}==>REDACTED_GOOGLE_MAPS_KEY
regex:SECRET_KEY=.*==>SECRET_KEY=REDACTED
regex:postgresql\+asyncpg://[^:]+:[^@]+@==>postgresql+asyncpg://REDACTED:REDACTED@
EOF
# Add the Firebase apiKey / appId / messagingSenderId literals from the pre-PR
# environment*.ts to expressions.txt as `literal:<value>==>REDACTED` lines before running.
git filter-repo --replace-text ../expressions.txt

# Sanity: nothing left
git log --all --oneline -- API-Fast/.env | wc -l          # expect 0
git grep -I -l 'AIza' $(git rev-list --all) | wc -l       # expect 0
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
| 2 | Google Maps API key `AIza…` | `index.html` in history (public bundle too) | Google Cloud Console → APIs & Services → Credentials → **create a new key** restricted to HTTP referrers (`https://<your-domain>/*`) and to Maps JavaScript API + Places API only → set `GOOGLE_MAPS_API_KEY` in `.env` → `docker compose up -d admin` (no rebuild needed) → **delete** the old key | Old kiosk/admin tabs show the OSM fallback until reloaded |
| 3 | Firebase web config | `environment*.ts` in history | Firebase console → Project settings → check whether the web app is still needed. App code does not use it: **delete the web app / restrict the API key** (Google Cloud → Credentials → the auto-created "Browser key (auto created by Firebase)") | None for DPU (unused) |
| 4 | `POSTGRES_PASSWORD` / `DATABASE_URL` password | `API-Fast/.env` in history and compose default `dpu_secret` | Generate a strong password → `ALTER USER dpu WITH PASSWORD '<new>';` on the running DB (and the shared `dev-postgres` user if used) → update `POSTGRES_PASSWORD` / `DATABASE_URL` in `.env` → `docker compose up -d api api-gpu1` → verify `/ready` and one check-in | Short API outage during restart; `scripts/backup.sh` must get the new password |
| 5 | Any value in `.env` copied from the leaked file | `SMTP_PASSWORD`, `LINE_CHANNEL_ACCESS_TOKEN`, `WEBHOOK_SIGNING_SECRET`, `FACE_CORE_API_KEY`, `S3_*` | Rotate at the provider if they were ever the same as a value in git | Webhook consumers need the new signing secret |

Evidence to keep in the change ticket: date/time of each rotation, who did it, and the output of the sanity commands in §2.

## 5. Preventing recurrence

- `.gitignore` now blocks `.env*`, face image folders, scratch spreadsheets and load-test dumps; `*.example` files are the only tracked templates.
- Add a secret scanner to CI before merging (`gitleaks detect --redact` in `.gitlab-ci.yml` `lint` stage, or GitHub secret scanning + push protection on the repo).
- Pre-commit hook suggestion: `pre-commit` with `gitleaks` and `check-added-large-files --maxkb=500`.
- Runtime secrets belong in `.env` (Docker) or the orchestrator's secret store, never in `index.html`, `environment*.ts`, or docs.
