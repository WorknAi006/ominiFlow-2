"""
WhatsApp media download worker.

    python -m app.workers.whatsapp_media            # one batch
    python -m app.workers.whatsapp_media --loop     # poll continuously

Safe to run several instances (rows are claimed with FOR UPDATE SKIP
LOCKED plus a short lease). A future Celery/Redis task should call
media_service.process_pending_media() the same way.
"""
import argparse
import logging
import time

from app.core.database import SessionLocal
from app.services.media_service import process_pending_media

logger = logging.getLogger("app.workers.whatsapp_media")


def run_once(batch_size: int) -> dict[str, int]:
    db = SessionLocal()
    try:
        return process_pending_media(db, limit=batch_size)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Download pending WhatsApp media.")
    parser.add_argument("--loop", action="store_true", help="Poll continuously.")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between polls.")
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    while True:
        counts = run_once(args.batch_size)
        if counts:
            logger.info("Processed media batch: %s", counts)
        if not args.loop:
            break
        if sum(counts.values()) < args.batch_size:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
