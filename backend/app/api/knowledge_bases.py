import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from app.api.dependencies import DbSession, CurrentTenant, require_permission
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate, KnowledgeBaseResponse, KnowledgeBaseUpdate, KnowledgeBaseDetailResponse,
    KnowledgeDocumentCreate, KnowledgeDocumentResponse, KnowledgeSearchRequest, KnowledgeSearchResult
)
from app.services import knowledge_base_service
from app.services.retrieval_service import semantic_search, SemanticSearchDeferredError, RetrievalError

router = APIRouter(tags=["Knowledge Base"])

@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("ai:update"))])
def create_knowledge_base(data: KnowledgeBaseCreate, tenant: CurrentTenant, db: DbSession):
    return knowledge_base_service.create_knowledge_base(db, tenant.id, data)

@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse], dependencies=[Depends(require_permission("ai:read"))])
def list_knowledge_bases(tenant: CurrentTenant, db: DbSession):
    return knowledge_base_service.list_knowledge_bases(db, tenant.id)

@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseDetailResponse, dependencies=[Depends(require_permission("ai:read"))])
def get_knowledge_base(kb_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    try:
        kb = knowledge_base_service.get_knowledge_base(db, tenant.id, kb_id)
        docs = knowledge_base_service.list_documents(db, tenant.id, kb_id)
        return {**kb.__dict__, "documents": docs}
    except knowledge_base_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse, dependencies=[Depends(require_permission("ai:update"))])
def update_knowledge_base(kb_id: uuid.UUID, data: KnowledgeBaseUpdate, tenant: CurrentTenant, db: DbSession):
    try:
        return knowledge_base_service.update_knowledge_base(db, tenant.id, kb_id, data)
    except knowledge_base_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/knowledge-bases/{kb_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("ai:update"))])
def delete_knowledge_base(kb_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    try:
        knowledge_base_service.delete_knowledge_base(db, tenant.id, kb_id)
    except knowledge_base_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/knowledge-bases/{kb_id}/documents", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("ai:update"))])
def add_document(kb_id: uuid.UUID, data: KnowledgeDocumentCreate, tenant: CurrentTenant, db: DbSession):
    try:
        return knowledge_base_service.add_document(db, tenant.id, kb_id, data)
    except knowledge_base_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[KnowledgeDocumentResponse], dependencies=[Depends(require_permission("ai:read"))])
def list_documents(kb_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    try:
        return knowledge_base_service.list_documents(db, tenant.id, kb_id)
    except knowledge_base_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/knowledge-bases/{kb_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("ai:update"))])
def delete_document(kb_id: uuid.UUID, doc_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    try:
        knowledge_base_service.delete_document(db, tenant.id, kb_id, doc_id)
    except knowledge_base_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/knowledge-bases/{kb_id}/documents/upload", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("ai:update"))])
def upload_document(kb_id: uuid.UUID, tenant: CurrentTenant, db: DbSession, file: UploadFile = File(...)):
    try:
        return knowledge_base_service.upload_document(db, tenant.id, kb_id, file)
    except knowledge_base_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge-bases/{kb_id}/search", response_model=list[KnowledgeSearchResult], dependencies=[Depends(require_permission("ai:read"))])
def search_knowledge_base(kb_id: uuid.UUID, data: KnowledgeSearchRequest, tenant: CurrentTenant, db: DbSession):
    try:
        # Verify ownership
        knowledge_base_service.get_knowledge_base(db, tenant.id, kb_id)
        
        # Execute search
        from app.services import retrieval_service
        
        if data.search_mode == "keyword":
            results = retrieval_service.keyword_search(db, tenant.id, data.query, limit=data.limit, kb_id=kb_id)
        else:
            results = retrieval_service.semantic_search(db, tenant.id, data.query, limit=data.limit, kb_id=kb_id)
        return results
    except knowledge_base_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SemanticSearchDeferredError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except RetrievalError as e:
        raise HTTPException(status_code=500, detail=str(e))
