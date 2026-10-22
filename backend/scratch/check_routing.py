import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import Flow, Keyword, TenantRoutingConfig

db = SessionLocal()
tenant_id = "5d75bcfd-595a-4c40-92ad-e203de27f9e9"

print("--- KEYWORDS ---")
keywords = db.query(Keyword).filter(Keyword.tenant_id == tenant_id).all()
for kw in keywords:
    print(f"Keyword: '{kw.keyword_text}' match={kw.match_type} active={kw.is_active} flow_id={kw.flow_id} reply_text='{kw.reply_text}'")

print("--- ROUTING CONFIG ---")
rc = db.query(TenantRoutingConfig).filter(TenantRoutingConfig.tenant_id == tenant_id).first()
if rc:
    print(f"Fallback action: {rc.fallback_action}, flow_id: {rc.fallback_flow_id}")
else:
    print("No TenantRoutingConfig found")

print("--- FLOWS ---")
flows = db.query(Flow).filter(Flow.tenant_id == tenant_id).all()
for f in flows:
    print(f"Flow: '{f.name}' status={f.status} id={f.id}")
db.close()
