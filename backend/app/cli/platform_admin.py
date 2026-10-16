"""Grant or revoke platform super-admin access for an existing user."""
import argparse
import logging

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--grant", action="store_true")
    action.add_argument("--revoke", action="store_true")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
        if user is None:
            parser.error("No user exists with that email.")
        user.is_platform_super_admin = args.grant
        db.commit()
        action_name = "granted" if args.grant else "revoked"
        print(f"Platform super-admin access {action_name} for {user.email}.")
    except Exception:
        db.rollback()
        logging.exception("Could not update platform super-admin access.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
