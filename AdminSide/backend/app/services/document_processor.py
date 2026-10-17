import logging
import uuid
import csv
import io

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.knowledge_base import KnowledgeDocument, KnowledgeDocumentChunk
from app.storage import get_storage

logger = logging.getLogger(__name__)

def extract_text(content: bytes, mime_type: str) -> str:
    if mime_type in ("text/plain", "text/markdown"):
        return content.decode("utf-8", errors="replace")
    elif mime_type == "text/csv":
        text = content.decode("utf-8", errors="replace")
        f = io.StringIO(text)
        reader = csv.reader(f)
        return "\n".join([", ".join(row) for row in reader])
    else:
        raise ValueError(f"Unsupported extraction format: {mime_type}")

def chunk_text(text: str, max_length: int = 1000, overlap: int = 200) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + max_length, text_len)
        chunks.append(text[start:end])
        if end == text_len:
            break
        start += max_length - overlap
    return chunks

def process_single_document(db: Session, doc_id: uuid.UUID) -> str:
    """Processes a single pending document, safe to run concurrently."""
    doc = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.id == doc_id,
        KnowledgeDocument.processing_status == "pending"
    ).with_for_update(skip_locked=True).first()

    if not doc:
        return "skipped"
        
    doc.processing_status = "processing"
    db.commit()
    
    try:
        storage = get_storage()
        if not doc.storage_key:
            raise ValueError("No storage key associated with document.")
            
        chunks_generator = storage.iter_chunks(doc.storage_key)
        
        content = b""
        for chunk in chunks_generator:
            content += chunk
            if len(content) > 30 * 1024 * 1024:
                raise ValueError("File content excessively large during extraction.")
                
        extracted = extract_text(content, doc.mime_type or "text/plain")
        if not extracted.strip():
            raise ValueError("Document yielded empty text.")
            
        text_chunks = chunk_text(extracted)
        
        for idx, text_chunk in enumerate(text_chunks):
            chunk_record = KnowledgeDocumentChunk(
                tenant_id=doc.tenant_id,
                document_id=doc.id,
                chunk_index=idx,
                text_content=text_chunk
            )
            db.add(chunk_record)
            
        doc.processing_status = "ready"
        doc.error_summary = None
        db.commit()
        return "success"
        
    except Exception as e:
        db.rollback()
        failed_doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if failed_doc:
            failed_doc.processing_status = "failed"
            failed_doc.error_summary = str(e)[:1000]
            db.commit()
        return "failed"

def process_pending_documents(db: Session, limit: int = 10) -> dict[str, int]:
    doc_ids = db.scalars(
        select(KnowledgeDocument.id)
        .where(KnowledgeDocument.processing_status == "pending")
        .order_by(KnowledgeDocument.created_at.asc())
        .limit(limit)
    ).all()
    
    db.rollback()
    
    results = {"success": 0, "failed": 0, "skipped": 0}
    for doc_id in doc_ids:
        res = process_single_document(db, doc_id)
        results[res] += 1
        
    return results
