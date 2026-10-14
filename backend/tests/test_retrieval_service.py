import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from tests.base import DatabaseTestCase

from app.models.knowledge_base import KnowledgeChunkEmbedding
from app.services.retrieval_service import semantic_search, SemanticSearchDeferredError, RetrievalError

class TestRetrievalService(DatabaseTestCase):
    @classmethod
    def create_fixtures(cls) -> None:
        cls.tenant1 = cls.make_tenant("Tenant 1")
        cls.user1 = cls.make_member(cls.tenant1, "OWNER")
        
        cls.tenant2 = cls.make_tenant("Tenant 2")
        cls.user2 = cls.make_member(cls.tenant2, "OWNER")

    def test_empty_query(self):
        # Empty query should return empty list without contacting provider
        res = semantic_search(self.db, self.tenant1.id, "")
        self.assertEqual(res, [])
        
        res2 = semantic_search(self.db, self.tenant1.id, "   ")
        self.assertEqual(res2, [])

    def test_semantic_search_deferred(self):
        # Querying with a mock provider should raise the deferred error since we lack pgvector
        with self.assertRaises(SemanticSearchDeferredError):
            semantic_search(self.db, self.tenant1.id, "What is omniflow?")

    from unittest.mock import patch
    @patch("app.services.retrieval_service.get_embedding_provider")
    def test_provider_errors(self, mock_get_provider):
        mock_provider = mock_get_provider.return_value
        mock_provider.embed_text.side_effect = Exception("API Key Invalid")
        
        with self.assertRaises(RetrievalError) as context:
            semantic_search(self.db, self.tenant1.id, "search query")
        
        self.assertIn("API Key Invalid", str(context.exception))

    def test_duplicate_embedding_prevention(self):
        from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentChunk
        kb = KnowledgeBase(id=uuid.uuid4(), tenant_id=self.tenant1.id, name="Test KB")
        doc = KnowledgeDocument(id=uuid.uuid4(), tenant_id=self.tenant1.id, knowledge_base_id=kb.id, title="test doc", source_type="file")
        chunk = KnowledgeDocumentChunk(id=uuid.uuid4(), tenant_id=self.tenant1.id, document_id=doc.id, chunk_index=0, text_content="content")
        self.db.add_all([kb, doc, chunk])
        self.db.flush()
        
        chunk_id = chunk.id
        emb1 = KnowledgeChunkEmbedding(
            id=uuid.uuid4(),
            tenant_id=self.tenant1.id,
            chunk_id=chunk_id,
            embedding_model="mock-embedding-model",
            embedding_version="1.0",
            embedding=[0.1] * 1536
        )
        self.db.add(emb1)
        self.db.commit()
        
        emb2 = KnowledgeChunkEmbedding(
            id=uuid.uuid4(),
            tenant_id=self.tenant1.id,
            chunk_id=chunk_id, # Same chunk
            embedding_model="mock-embedding-model", # Same model
            embedding_version="1.0", # Same version
            embedding=[0.2] * 1536
        )
        self.db.add(emb2)
        
        with self.assertRaises(IntegrityError):
            self.db.commit()
            
        self.db.rollback()

    def test_keyword_search(self):
        from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentChunk
        from app.services.retrieval_service import keyword_search
        
        # Setup data
        kb1 = KnowledgeBase(id=uuid.uuid4(), tenant_id=self.tenant1.id, name="KB1")
        kb2 = KnowledgeBase(id=uuid.uuid4(), tenant_id=self.tenant1.id, name="KB2")
        kb3 = KnowledgeBase(id=uuid.uuid4(), tenant_id=self.tenant2.id, name="KB3 (Tenant 2)")
        
        # Doc 1: ready (Tenant 1, KB 1)
        doc1 = KnowledgeDocument(id=uuid.uuid4(), tenant_id=self.tenant1.id, knowledge_base_id=kb1.id, title="Doc1", source_type="text", processing_status="ready")
        chunk1_1 = KnowledgeDocumentChunk(id=uuid.uuid4(), tenant_id=self.tenant1.id, document_id=doc1.id, chunk_index=0, text_content="The quick brown fox jumps over the lazy dog.")
        chunk1_2 = KnowledgeDocumentChunk(id=uuid.uuid4(), tenant_id=self.tenant1.id, document_id=doc1.id, chunk_index=1, text_content="An apple a day keeps the doctor away.")
        
        # Doc 2: pending (Tenant 1, KB 1) - shouldn't be matched
        doc2 = KnowledgeDocument(id=uuid.uuid4(), tenant_id=self.tenant1.id, knowledge_base_id=kb1.id, title="Doc2", source_type="text", processing_status="pending")
        chunk2_1 = KnowledgeDocumentChunk(id=uuid.uuid4(), tenant_id=self.tenant1.id, document_id=doc2.id, chunk_index=0, text_content="The quick brown fox also appears here but shouldn't match.")
        
        # Doc 3: ready (Tenant 1, KB 2) - should match but only if kb_id not restricted to kb1
        doc3 = KnowledgeDocument(id=uuid.uuid4(), tenant_id=self.tenant1.id, knowledge_base_id=kb2.id, title="Doc3", source_type="text", processing_status="ready")
        chunk3_1 = KnowledgeDocumentChunk(id=uuid.uuid4(), tenant_id=self.tenant1.id, document_id=doc3.id, chunk_index=0, text_content="A brown dog is playing in the park.")
        
        # Doc 4: ready (Tenant 2, KB 3) - shouldn't match for tenant 1
        doc4 = KnowledgeDocument(id=uuid.uuid4(), tenant_id=self.tenant2.id, knowledge_base_id=kb3.id, title="Doc4", source_type="text", processing_status="ready")
        chunk4_1 = KnowledgeDocumentChunk(id=uuid.uuid4(), tenant_id=self.tenant2.id, document_id=doc4.id, chunk_index=0, text_content="The brown fox is a tenant 2 secret.")
        
        self.db.add_all([kb1, kb2, kb3, doc1, chunk1_1, chunk1_2, doc2, chunk2_1, doc3, chunk3_1, doc4, chunk4_1])
        self.db.flush()
        
        # 1. Basic matching
        results = keyword_search(self.db, self.tenant1.id, "apple")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], chunk1_2.id)
        
        # 2. Non-matching queries and empty queries
        self.assertEqual(keyword_search(self.db, self.tenant1.id, "elephant"), [])
        self.assertEqual(keyword_search(self.db, self.tenant1.id, ""), [])
        self.assertEqual(keyword_search(self.db, self.tenant1.id, "   "), [])
        
        # 3. Tenant isolation
        results = keyword_search(self.db, self.tenant1.id, "secret")
        self.assertEqual(len(results), 0) # tenant 2 doc shouldn't be matched
        
        results = keyword_search(self.db, self.tenant2.id, "fox")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], chunk4_1.id)
        
        # 4. Exclusion of non-READY documents
        # "fox" is in doc1 (ready), doc2 (pending), doc4 (tenant2).
        results = keyword_search(self.db, self.tenant1.id, "fox")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], chunk1_1.id) # Only chunk1_1 is returned, chunk2_1 is ignored
        
        # 5. Knowledge Base ownership (Filter by kb_id)
        results = keyword_search(self.db, self.tenant1.id, "dog", kb_id=kb1.id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], chunk1_1.id)
        
        # Across KBs (no kb_id)
        results = keyword_search(self.db, self.tenant1.id, "dog")
        self.assertEqual(len(results), 2)
        # Verify ordering (deterministic based on ts_rank and chunk.id)
        # Depending on ts_rank, either chunk1_1 or chunk3_1 might be first. We just verify both are returned.
        chunk_ids = {r["chunk_id"] for r in results}
        self.assertIn(chunk1_1.id, chunk_ids)
        self.assertIn(chunk3_1.id, chunk_ids)
        
        # 6. Result Limits
        results = keyword_search(self.db, self.tenant1.id, "dog", limit=1)
        self.assertEqual(len(results), 1)
