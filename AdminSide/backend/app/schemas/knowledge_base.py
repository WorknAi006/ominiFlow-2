import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class KnowledgeDocumentBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source_type: str = Field(min_length=1, max_length=50)
    source_reference: str | None = None

class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    pass

class KnowledgeDocumentResponse(KnowledgeDocumentBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    processing_status: str
    error_summary: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    status: str | None = Field(default=None, max_length=50)

class KnowledgeBaseResponse(KnowledgeBaseBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class KnowledgeBaseDetailResponse(KnowledgeBaseResponse):
    documents: list[KnowledgeDocumentResponse] = Field(default_factory=list)

class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)
    search_mode: str = Field(default="semantic", description="Mode of search: 'semantic' or 'keyword'")

class KnowledgeSearchResult(BaseModel):
    chunk_id: uuid.UUID
    text: str
    distance: float | None = None
    
    model_config = ConfigDict(from_attributes=True)
