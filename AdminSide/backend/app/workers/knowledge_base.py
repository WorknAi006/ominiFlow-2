"""
Knowledge Base document processing worker.

    python -m app.workers.knowledge_base            # one batch
    python -m app.workers.knowledge_base --loop     # poll continuously

"""
import argparse
import logging
import time

from app.core.database import SessionLocal
from app.services.document_processor import process_pending_documents

logger = logging.getLogger("app.workers.knowledge_base")

def run_once(batch_size: int) -> dict[str, int]:
    db = SessionLocal()
    try:
        return process_pending_documents(db, limit=batch_size)
    finally:
        db.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="Process pending Knowledge Base documents.")
    parser.add_argument("--loop", action="store_true", help="Poll continuously.")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between polls.")
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    while True:
        counts = run_once(args.batch_size)
        if any(counts.values()):
            logger.info("Processed documents batch: %s", counts)
        if not args.loop:
            break
        if sum(counts.values()) < args.batch_size:
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
