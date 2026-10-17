import uuid
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

class KnowledgeBase(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_bases"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", server_default="active", nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_knowledge_bases_tenant_id"),
    )

class KnowledgeDocument(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_documents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", server_default="pending", nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(400), nullable=True)
    storage_backend: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id"],
            ["knowledge_bases.tenant_id", "knowledge_bases.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("tenant_id", "id", name="uq_knowledge_documents_tenant_id"),
    )

class KnowledgeDocumentChunk(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_document_chunks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "document_id"],
            ["knowledge_documents.tenant_id", "knowledge_documents.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunks_doc_index"),
        UniqueConstraint("tenant_id", "id", name="uq_knowledge_chunks_tenant_id"),
    )

class KnowledgeChunkEmbedding(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_chunk_embeddings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")

    # Fallback to standard PostgreSQL ARRAY(Float) since pgvector is not installed.
    from sqlalchemy import ARRAY, Float
    embedding: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "chunk_id"],
            ["knowledge_document_chunks.tenant_id", "knowledge_document_chunks.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("chunk_id", "embedding_model", "embedding_version", name="uq_chunk_embedding_model_version"),
        UniqueConstraint("tenant_id", "id", name="uq_knowledge_embeddings_tenant_id"),
    )
