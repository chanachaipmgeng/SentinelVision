"""Entrypoint: ``python -m src.worker [--once] [--jobs a,b] [--worker-id ID] [--metrics-port N]``."""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from ..config.settings import settings
from ..security.jwt import assert_secret_configured
from ..services.observability import configure_logging, setup_tracing, shutdown_tracing
from .runner import WorkerRunner, parse_job_list, run_jobs_once, wait_for_database

logger = logging.getLogger("dpu.worker")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m src.worker", description=__doc__)
    parser.add_argument("--once", action="store_true", help="run each job once and exit (cron mode)")
    parser.add_argument(
        "--jobs",
        default=settings.WORKER_JOBS,
        help="comma list of jobs to run (outbox,retention,imports); default from WORKER_JOBS",
    )
    parser.add_argument("--worker-id", default=None, help="override WORKER_ID (shown in import_job.lockedBy)")
    parser.add_argument(
        "--metrics-port",
        type=int,
        default=settings.WORKER_METRICS_PORT,
        help="Prometheus /metrics port for the long-running mode (0 = disabled)",
    )
    parser.add_argument("--db-wait-attempts", type=int, default=60, help="SELECT 1 retries before giving up")
    return parser.parse_args(argv)


async def _amain(args: argparse.Namespace) -> int:
    from ..services.storage_service import ensure_dirs

    job_names = parse_job_list(args.jobs)
    ensure_dirs()
    await wait_for_database(attempts=args.db_wait_attempts)

    if args.once:
        results = await run_jobs_once(job_names, worker_id=args.worker_id)
        logger.info("single run finished", extra={"results": results})
        return 0 if all(results.values()) else 1

    if args.metrics_port and args.metrics_port > 0:
        from prometheus_client import start_http_server

        start_http_server(int(args.metrics_port))
        logger.info("worker metrics on :%s/metrics", args.metrics_port)

    runner = WorkerRunner(job_names, worker_id=args.worker_id)
    await runner.run_forever(handle_signals=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    configure_logging("worker")
    # Same guard as the API: a weak SECRET_KEY must not slip through a sidecar either.
    assert_secret_configured()
    setup_tracing(service_name=settings.OTEL_SERVICE_NAME or "dpu-worker")
    try:
        return asyncio.run(_amain(args))
    except KeyboardInterrupt:  # pragma: no cover
        return 0
    finally:
        shutdown_tracing()


if __name__ == "__main__":
    sys.exit(main())
