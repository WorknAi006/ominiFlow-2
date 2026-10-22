import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import Flow

db = SessionLocal()
flows = db.query(Flow).all()
print(f"Total flows: {len(flows)}")
for f in flows:
    print(f"\nFlow ID: {f.id}, Name: {f.name}, Status: {f.status}, Tenant: {f.tenant_id}")
    print(f"  Nodes count: {len(f.nodes or [])}")
    for n in (f.nodes or []):
        d = n.get("data") or {}
        mt = d.get("messageType")
        buttons = d.get("buttons") or []
        items = d.get("listItems") or []
        media = d.get("mediaUrl") or d.get("mediaKey")
        print(f"    Node id={n.get('id')} type={mt} isStart={d.get('isStart')}")
        if buttons:
            print(f"      Buttons: {[b.get('id', '') + ':' + b.get('title', '') + '(' + b.get('kind', 'reply') + ')' for b in buttons]}")
        if items:
            print(f"      List items: {[it.get('id', '') + ':' + it.get('title', '') for it in items]}")
        if media:
            print(f"      Media: {media}")
    print(f"  Edges count: {len(f.edges or [])}")
    for e in (f.edges or []):
        print(f"    Edge: {e.get('source')} [handle: {e.get('sourceHandle')}] -> {e.get('target')}")
db.close()
