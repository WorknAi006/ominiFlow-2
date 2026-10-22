import os
import sys

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def seed_platform_admin(
    email: str = "admin@omniflow.io",
    password: str = "OmniflowAdmin2026!",
    first_name: str = "Platform",
    last_name: str = "Admin",
) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user:
            user.is_platform_super_admin = True
            user.is_active = True
            user.is_verified = True
            user.password_hash = hash_password(password)
            db.commit()
            print(f"Platform Super Admin '{email}' updated successfully.")
        else:
            user = User(
                email=email.lower(),
                password_hash=hash_password(password),
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                is_verified=True,
                is_platform_super_admin=True,
            )
            db.add(user)
            db.commit()
            print(f"Platform Super Admin '{email}' created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else os.getenv("SUPERADMIN_EMAIL", "admin@omniflow.io")
    password = sys.argv[2] if len(sys.argv) > 2 else os.getenv("SUPERADMIN_PASSWORD", "OmniflowAdmin2026!")
    seed_platform_admin(email=email, password=password)
