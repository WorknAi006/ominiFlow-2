import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.knowledge_base import KnowledgeDocumentChunk, KnowledgeChunkEmbedding, KnowledgeBase
from app.services.ai_provider import get_embedding_provider

class RetrievalError(Exception):
    pass

class SemanticSearchDeferredError(RetrievalError):
    pass

def semantic_search(db: Session, tenant_id: uuid.UUID, query: str, limit: int = 5, kb_id: uuid.UUID | None = None) -> List[Dict[str, Any]]:
    """
    Performs a tenant-scoped semantic search over document chunks.
    
    This function embeds the search query using the configured AI provider,
    then retrieves the most semantically similar text chunks safely scoped to the tenant
    and optionally a specific knowledge base.
    """
    if not query or not query.strip():
        return []

    # 1. Fetch Provider (real OpenAI when OPENAI_API_KEY is set, else mock).
    provider = get_embedding_provider(tenant_id.hex)

    # 2. Embed Query.
    try:
        query_vector = provider.embed_text(query)
    except Exception as e:
        raise RetrievalError(f"Embedding provider failed: {e}")

    # 3. Retrieve Chunks. Execution requires performant vector similarity,
    # which needs the 'pgvector' extension (PostgreSQL ARRAY(Float) cannot
    # index cosine/dot distance). The embedding provider and model foundation
    # are complete, but search execution is deferred until pgvector is enabled.
    _ = query_vector
    raise SemanticSearchDeferredError(
        "Semantic search requires the 'pgvector' extension or an external vector database. "
        "The embedding provider and model foundation are complete, but execution is deferred."
    )

    # FUTURE IMPLEMENTATION (with pgvector):
    # results = db.query(KnowledgeDocumentChunk, KnowledgeChunkEmbedding).join(
    #     KnowledgeChunkEmbedding, KnowledgeDocumentChunk.id == KnowledgeChunkEmbedding.chunk_id
    # ).filter(
    #     KnowledgeDocumentChunk.tenant_id == tenant_id
    # ).order_by(
    #     KnowledgeChunkEmbedding.embedding.cosine_distance(query_vector)
    # ).limit(limit).all()
    #
    # return [{"chunk_id": chunk.id, "text": chunk.text_content, "distance": ...} for chunk, emb in results]

def check_tenant_has_knowledge_bases(db: Session, tenant_id: uuid.UUID) -> bool:
    """Helper to verify if a tenant even has any knowledge bases to search."""
    kb = db.execute(select(KnowledgeBase.id).filter_by(tenant_id=tenant_id).limit(1)).first()
    return kb is not None

def keyword_search(db: Session, tenant_id: uuid.UUID, query: str, limit: int = 5, kb_id: uuid.UUID | None = None) -> List[Dict[str, Any]]:
    """
    Performs a tenant-scoped keyword search over document chunks.
    Uses PostgreSQL full text search for matching.
    """
    if not query or not query.strip():
        return []
        
    from sqlalchemy import func
    from app.models.knowledge_base import KnowledgeDocument
    
    tsquery = func.plainto_tsquery('english', query)
    tsvector = func.to_tsvector('english', KnowledgeDocumentChunk.text_content)
    
    stmt = select(KnowledgeDocumentChunk).join(
        KnowledgeDocument, KnowledgeDocumentChunk.document_id == KnowledgeDocument.id
    ).filter(
        KnowledgeDocumentChunk.tenant_id == tenant_id,
        KnowledgeDocument.tenant_id == tenant_id,
        KnowledgeDocument.processing_status == 'ready',
        tsvector.op('@@')(tsquery)
    )
    
    if kb_id:
        stmt = stmt.filter(KnowledgeDocument.knowledge_base_id == kb_id)
        
    rank = func.ts_rank(tsvector, tsquery)
    stmt = stmt.order_by(rank.desc(), KnowledgeDocumentChunk.id).limit(limit)
    
    results = db.execute(stmt).scalars().all()
    
    return [
        {
            "chunk_id": chunk.id,
            "text": chunk.text_content,
            "distance": None
        }
        for chunk in results
    ]
