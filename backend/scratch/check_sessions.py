import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import FlowSession, Message

db = SessionLocal()
tenant_id = "5d75bcfd-595a-4c40-92ad-e203de27f9e9"

print("--- FLOW SESSIONS ---")
sessions = db.query(FlowSession).filter(FlowSession.tenant_id == tenant_id).order_by(FlowSession.created_at.desc()).limit(10).all()
for s in sessions:
    print(f"Session {s.id}: status={s.status} wait_kind={s.wait_kind} waiting_node={s.waiting_node_id} pending_reply='{s.pending_reply}' detail='{s.detail}' current_node={s.current_node_id}")

print("\n--- RECENT MESSAGES ---")
messages = db.query(Message).filter(Message.tenant_id == tenant_id).order_by(Message.created_at.desc()).limit(15).all()
for m in messages:
    print(f"Message {m.id}: dir={m.direction} type={m.message_type} text='{m.text}' metadata={m.metadata}")
db.close()
