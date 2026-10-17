"""
WhatsApp event worker.

    python -m app.workers.whatsapp_events            # process one batch
    python -m app.workers.whatsapp_events --loop     # poll continuously

Safe to run several instances: events are claimed with
FOR UPDATE SKIP LOCKED. A future Celery/Redis task should call
whatsapp_event_processor.process_pending_events() the same way.
"""
import argparse
import logging
import time

from app.core.database import SessionLocal
from app.services.whatsapp_event_processor import process_pending_events

logger = logging.getLogger("app.workers.whatsapp_events")


def run_once(batch_size: int) -> dict[str, int]:
    db = SessionLocal()
    try:
        return process_pending_events(db, limit=batch_size)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Process received WhatsApp events.")
    parser.add_argument("--loop", action="store_true", help="Poll continuously.")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between polls.")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    while True:
        counts = run_once(args.batch_size)
        if counts:
            logger.info("Processed batch: %s", counts)
        if not args.loop:
            break
        # Drain quickly while there is work; otherwise wait.
        if sum(counts.values()) < args.batch_size:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
