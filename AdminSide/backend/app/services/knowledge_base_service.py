import uuid
import re
from fastapi import UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.storage import get_storage

from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeDocumentCreate

class NotFoundError(Exception):
    pass

def create_knowledge_base(db: Session, tenant_id: uuid.UUID, data: KnowledgeBaseCreate) -> KnowledgeBase:
    kb = KnowledgeBase(tenant_id=tenant_id, name=data.name, description=data.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb

def list_knowledge_bases(db: Session, tenant_id: uuid.UUID) -> list[KnowledgeBase]:
    return list(db.scalars(select(KnowledgeBase).filter_by(tenant_id=tenant_id).order_by(KnowledgeBase.created_at.desc())).all())

def get_knowledge_base(db: Session, tenant_id: uuid.UUID, kb_id: uuid.UUID) -> KnowledgeBase:
    kb = db.scalars(select(KnowledgeBase).filter_by(tenant_id=tenant_id, id=kb_id)).first()
    if not kb:
        raise NotFoundError("Knowledge Base not found")
    return kb

def update_knowledge_base(db: Session, tenant_id: uuid.UUID, kb_id: uuid.UUID, data: KnowledgeBaseUpdate) -> KnowledgeBase:
    kb = get_knowledge_base(db, tenant_id, kb_id)
    if data.name is not None:
        kb.name = data.name
    if data.description is not None:
        kb.description = data.description
    if data.status is not None:
        kb.status = data.status
    db.commit()
    db.refresh(kb)
    return kb

def delete_knowledge_base(db: Session, tenant_id: uuid.UUID, kb_id: uuid.UUID) -> None:
    kb = get_knowledge_base(db, tenant_id, kb_id)
    db.delete(kb)
    db.commit()

def add_document(db: Session, tenant_id: uuid.UUID, kb_id: uuid.UUID, data: KnowledgeDocumentCreate) -> KnowledgeDocument:
    kb = get_knowledge_base(db, tenant_id, kb_id) # ensure it exists
    doc = KnowledgeDocument(
        tenant_id=tenant_id,
        knowledge_base_id=kb.id,
        title=data.title,
        source_type=data.source_type,
        source_reference=data.source_reference
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

def list_documents(db: Session, tenant_id: uuid.UUID, kb_id: uuid.UUID) -> list[KnowledgeDocument]:
    get_knowledge_base(db, tenant_id, kb_id) # ensure it exists
    return list(db.scalars(select(KnowledgeDocument).filter_by(tenant_id=tenant_id, knowledge_base_id=kb_id).order_by(KnowledgeDocument.created_at.desc())).all())

def get_document(db: Session, tenant_id: uuid.UUID, kb_id: uuid.UUID, doc_id: uuid.UUID) -> KnowledgeDocument:
    doc = db.scalars(select(KnowledgeDocument).filter_by(tenant_id=tenant_id, knowledge_base_id=kb_id, id=doc_id)).first()
    if not doc:
        raise NotFoundError("Document not found")
    return doc

def delete_document(db: Session, tenant_id: uuid.UUID, kb_id: uuid.UUID, doc_id: uuid.UUID) -> None:
    doc = get_document(db, tenant_id, kb_id, doc_id)
    db.delete(doc)
    db.commit()

def update_document_status(db: Session, tenant_id: uuid.UUID, kb_id: uuid.UUID, doc_id: uuid.UUID, processing_status: str, error_summary: str | None = None) -> KnowledgeDocument:
    doc = get_document(db, tenant_id, kb_id, doc_id)
    doc.processing_status = processing_status
    doc.error_summary = error_summary
    db.commit()
    db.refresh(doc)
    return doc

def sanitize_filename(name: str) -> str:
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")

def upload_document(db: Session, tenant_id: uuid.UUID, kb_id: uuid.UUID, file: UploadFile) -> KnowledgeDocument:
    kb = get_knowledge_base(db, tenant_id, kb_id)
    
    MAX_SIZE = 25 * 1024 * 1024 # 25MB
    content = bytearray()
    while True:
        chunk = file.file.read(1024 * 1024) # 1MB chunks
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_SIZE:
            raise ValueError("File size exceeds limit of 25MB")
            
    content_bytes = bytes(content)
    file_size = len(content_bytes)
    
    mime_type = file.content_type
    original_filename = sanitize_filename(file.filename or "uploaded_file")
    
    supported_mimes = {
        "text/plain": ".txt",
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/csv": ".csv",
        "text/markdown": ".md"
    }
    
    if mime_type not in supported_mimes:
        raise ValueError(f"Unsupported file type: {mime_type}")
        
    extension = supported_mimes[mime_type]
    
    doc_id = uuid.uuid4()
    storage = get_storage()
    storage_key = f"tenants/{tenant_id.hex}/knowledge_bases/{kb.id.hex}/{doc_id.hex}{extension}"
    
    doc = KnowledgeDocument(
        id=doc_id,
        tenant_id=tenant_id,
        knowledge_base_id=kb.id,
        title=original_filename,
        source_type="file",
        processing_status="pending", # Pending because extraction is deferred
        original_filename=original_filename,
        mime_type=mime_type,
        file_size=file_size,
        storage_key=storage_key,
        storage_backend=storage.backend_name,
    )
    db.add(doc)
    
    try:
        storage.save(storage_key, content_bytes, mime_type)
        db.commit()
        db.refresh(doc)
    except Exception as e:
        db.rollback()
        try:
            storage.delete(storage_key)
        except Exception:
            pass
        raise RuntimeError(f"Failed to save file: {e}")
        
    return doc
