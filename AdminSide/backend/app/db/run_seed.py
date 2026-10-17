from app.core.database import SessionLocal
from app.db.seed import (
    seed_permissions,
    seed_role_permissions,
    seed_system_roles,
)


def main() -> None:
    db = SessionLocal()

    try:
        seed_system_roles(db)
        print("System roles seeded successfully.")

        seed_permissions(db)
        print("Permissions seeded successfully.")

        seed_role_permissions(db)
        print("Role permissions seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
