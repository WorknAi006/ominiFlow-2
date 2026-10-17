import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.tenant import Tenant
from app.models.role import Role
from app.models.tenant_membership import TenantMembership

def seed_real_data():
    db = SessionLocal()
    try:
        # 1. Fetch system roles
        roles = {r.name.upper(): r for r in db.query(Role).all()}
        if not roles:
            print("No roles found. Please run system seed first.")
            return

        # 2. Tenants to seed
        tenants_data = [
            {
                "name": "Acme Global Solutions",
                "slug": "acme-global",
                "email": "support@acmeglobal.com",
                "phone": "+1-800-555-0199",
                "description": "Global enterprise customer engagement and omnichannel communication.",
            },
            {
                "name": "Nova Retail Technologies",
                "slug": "nova-retail",
                "email": "help@novaretail.io",
                "phone": "+1-800-555-0144",
                "description": "Direct-to-consumer e-commerce customer messaging and live support.",
            },
            {
                "name": "Pulse Health Tech",
                "slug": "pulse-health",
                "email": "care@pulsehealth.co",
                "phone": "+1-800-555-0122",
                "description": "Patient concierge services and clinical communication platform.",
            },
        ]

        tenant_map = {}
        for t_info in tenants_data:
            existing_t = db.query(Tenant).filter(Tenant.slug == t_info["slug"]).first()
            if not existing_t:
                new_t = Tenant(
                    name=t_info["name"],
                    slug=t_info["slug"],
                    email=t_info["email"],
                    phone=t_info["phone"],
                    description=t_info["description"],
                    is_active=True,
                    is_deleted=False,
                )
                db.add(new_t)
                db.flush()
                tenant_map[t_info["slug"]] = new_t
                print(f"Created tenant: {new_t.name}")
            else:
                tenant_map[t_info["slug"]] = existing_t
                print(f"Tenant exists: {existing_t.name}")

        # 3. Real working users to seed
        common_password = hash_password("Omniflow2026!")

        users_data = [
            {
                "first_name": "Sarah",
                "last_name": "Jenkins",
                "email": "sarah.jenkins@acmeglobal.com",
                "tenant_slug": "acme-global",
                "role_name": "OWNER",
                "is_platform_admin": False,
            },
            {
                "first_name": "Marcus",
                "last_name": "Chen",
                "email": "marcus.chen@acmeglobal.com",
                "tenant_slug": "acme-global",
                "role_name": "ADMIN",
                "is_platform_admin": False,
            },
            {
                "first_name": "Emily",
                "last_name": "Watson",
                "email": "emily.watson@novaretail.io",
                "tenant_slug": "nova-retail",
                "role_name": "OWNER",
                "is_platform_admin": False,
            },
            {
                "first_name": "Alex",
                "last_name": "Rivera",
                "email": "alex.rivera@novaretail.io",
                "tenant_slug": "nova-retail",
                "role_name": "AGENT",
                "is_platform_admin": False,
            },
            {
                "first_name": "Aravind",
                "last_name": "Patel",
                "email": "aravind.patel@pulsehealth.co",
                "tenant_slug": "pulse-health",
                "role_name": "OWNER",
                "is_platform_admin": False,
            },
            {
                "first_name": "Clara",
                "last_name": "Oswald",
                "email": "clara.oswald@pulsehealth.co",
                "tenant_slug": "pulse-health",
                "role_name": "MANAGER",
                "is_platform_admin": False,
            },
        ]

        for u_info in users_data:
            existing_u = db.query(User).filter(User.email == u_info["email"]).first()
            if not existing_u:
                user = User(
                    email=u_info["email"],
                    password_hash=common_password,
                    first_name=u_info["first_name"],
                    last_name=u_info["last_name"],
                    is_active=True,
                    is_verified=True,
                    is_platform_admin=u_info["is_platform_admin"],
                )
                db.add(user)
                db.flush()
                print(f"Created real user: {user.first_name} {user.last_name} ({user.email})")
            else:
                user = existing_u
                print(f"User exists: {user.email}")

            tenant = tenant_map.get(u_info["tenant_slug"])
            role = roles.get(u_info["role_name"])
            if tenant and role:
                membership = db.query(TenantMembership).filter(
                    TenantMembership.tenant_id == tenant.id,
                    TenantMembership.user_id == user.id,
                ).first()
                if not membership:
                    new_mem = TenantMembership(
                        tenant_id=tenant.id,
                        user_id=user.id,
                        role_id=role.id,
                        status="active",
                    )
                    db.add(new_mem)
                    print(f"  Assigned {user.email} to {tenant.name} as {role.name}")

        db.commit()
        print("\nSeeding completed successfully! All real users and workspaces are active.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_real_data()
