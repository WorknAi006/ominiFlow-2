"""Deliver matched keyword → flow triggers through the channel providers.

Keyword matching records a ``keyword_triggers`` row inside the inbound
transaction; this worker picks those rows up after commit and sends the flow's
entry message (or the fallback reply text) through the connected provider, so
no provider HTTP call ever runs inside a webhook request.
"""
import argparse
import logging
import os
import signal
import socket
from threading import Event
import uuid

from app.core.database import SessionLocal
from app.services import flow_engine
from app.services.flow_runner import process_pending

logger = logging.getLogger("app.workers.flow_delivery")


def worker_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def run_once(batch_size: int = 50) -> dict[str, int]:
    db = SessionLocal()
    try:
        counts = process_pending(db, limit=batch_size)          # start flows / send replies
        replies = flow_engine.resume_pending_replies(db, batch_size)  # advance waiting flows
        delays = flow_engine.resume_due_delays(db, batch_size)        # resume elapsed delays
        counts["replies_resumed"] = replies["resumed"]
        counts["delays_resumed"] = delays["resumed"]
        return counts
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Deliver matched keyword/flow triggers.")
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
        logger.info("flow_delivery_shutdown_requested", extra={"worker_id": worker_id, "signal": signum})

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    logger.info("flow_delivery_worker_started", extra={"worker_id": worker_id})
    try:
        while not stopping.is_set():
            try:
                counts = run_once(args.batch_size)
                if counts.get("delivered") or counts.get("failed"):
                    logger.info("flow_delivery_batch", extra={"worker_id": worker_id, **counts})
            except Exception as exc:
                logger.error("flow_delivery_batch_failed", extra={"worker_id": worker_id, "error_type": type(exc).__name__})
            if not args.loop:
                break
            if not stopping.is_set():
                stopping.wait(max(0.5, args.interval))
    finally:
        logger.info("flow_delivery_worker_stopped", extra={"worker_id": worker_id})


if __name__ == "__main__":
    main()
