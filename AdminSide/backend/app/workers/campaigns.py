"""Poll and run durable campaign executions.

Uses the same PostgreSQL SKIP LOCKED worker pattern as the existing
automation workers.
"""
import argparse
import logging
import os
import signal
import socket
from threading import Event
import uuid

from app.core.database import SessionLocal
from app.services.campaign_execution_service import process_pending_recipients

logger = logging.getLogger("app.workers.campaigns")

def worker_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"

def run_once(batch_size: int = 50, worker_id: str = "campaign-worker") -> dict[str, int]:
    db = SessionLocal()
    try:
        return process_pending_recipients(db, limit=batch_size, worker_id=worker_id)
    finally:
        db.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="Process queued campaign messages.")
    parser.add_argument("--loop", action="store_true", help="Poll continuously.")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--worker-id", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    worker_id = args.worker_id or worker_identity()
    stopping = Event()

    def request_shutdown(signum, _frame):
        stopping.set()
        logger.info("campaign_worker_shutdown_requested", extra={"worker_id": worker_id, "signal": signum})

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    logger.info("campaign_worker_started", extra={"worker_id": worker_id})
    try:
        while not stopping.is_set():
            try:
                counts = run_once(args.batch_size, worker_id)
                if counts.get("processed"):
                    logger.info("campaign_worker_batch_completed", extra={"worker_id": worker_id, **counts})
            except Exception as exc:
                logger.error("campaign_worker_batch_failed", extra={"worker_id": worker_id, "error_type": type(exc).__name__})
            if not args.loop:
                break
            if not stopping.is_set():
                stopping.wait(max(0.1, args.interval))
    finally:
        logger.info("campaign_worker_stopped", extra={"worker_id": worker_id})

if __name__ == "__main__":
    main()
