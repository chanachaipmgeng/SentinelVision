"""Background worker service (B7).

Runs the notification outbox dispatcher, attendance cutoff, storage / sentinel / import-payload
retention, employee import processing, and Phase 4A CCTV face analysis outside the API process::

    python -m src.worker                  # long-running (docker-compose `worker` service)
    python -m src.worker --once           # run every job one time and exit (cron)
    python -m src.worker --once --jobs outbox,imports,cctv

The API runs the same loops in-process only when ``RUN_BACKGROUND_JOBS_IN_API=true``.
"""
from .runner import JOBS, WorkerRunner, run_jobs_once  # noqa: F401
