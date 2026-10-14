"""Periodically fire time-based ("chat stuck in a mode") automation rules.

The event-driven triggers run inline from their service hooks; this worker
only handles the time threshold that has no inbound event to ride on.
"""
import argparse
import logging
import os
import signal
import socket
from threading import Event
import uuid

from app.core.database import SessionLocal
from app.services.automation_execution_service import run_stuck_scan

logger = logging.getLogger("app.workers.automations")


def worker_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def run_once(batch_size: int = 200) -> dict[str, int]:
    db = SessionLocal()
    try:
        return run_stuck_scan(db, limit=batch_size)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fire time-based automation rules.")
    parser.add_argument("--loop", action="store_true", help="Poll continuously.")
    parser.add_argument("--interval", type=float, default=60.0)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--worker-id", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    worker_id = args.worker_id or worker_identity()
    stopping = Event()

    def request_shutdown(signum, _frame):
        stopping.set()
        logger.info("automation_worker_shutdown_requested", extra={"worker_id": worker_id, "signal": signum})

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    logger.info("automation_worker_started", extra={"worker_id": worker_id})
    try:
        while not stopping.is_set():
            try:
                counts = run_once(args.batch_size)
                if counts.get("processed"):
                    logger.info("automation_worker_batch_completed", extra={"worker_id": worker_id, **counts})
            except Exception as exc:
                logger.error("automation_worker_batch_failed", extra={"worker_id": worker_id, "error_type": type(exc).__name__})
            if not args.loop:
                break
            if not stopping.is_set():
                stopping.wait(max(1.0, args.interval))
    finally:
        logger.info("automation_worker_stopped", extra={"worker_id": worker_id})


if __name__ == "__main__":
    main()
