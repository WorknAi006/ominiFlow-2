import uuid
from unittest.mock import patch
from app.models.knowledge_base import KnowledgeDocument, KnowledgeDocumentChunk
from app.services.document_processor import chunk_text, extract_text, process_single_document
from tests.base import DatabaseTestCase

class TestDocumentProcessor(DatabaseTestCase):
    @classmethod
    def create_fixtures(cls) -> None:
        from app.models import Permission, RolePermission
        for p_name in ["ai:read", "ai:update"]:
            perm = cls.db.query(Permission).filter_by(name=p_name).first()
            if not perm:
                perm = Permission(name=p_name, description=p_name, is_active=True)
                cls.db.add(perm)
                cls.db.flush()
            owner_role = cls.role("OWNER")
            if not cls.db.query(RolePermission).filter_by(role_id=owner_role.id, permission_id=perm.id).first():
                cls.db.add(RolePermission(role_id=owner_role.id, permission_id=perm.id))
                
        cls.tenant1 = cls.make_tenant("Tenant 1")
        cls.user1 = cls.make_member(cls.tenant1, "OWNER")

    def test_chunk_text(self):
        text = "Hello world! This is a test string."
        chunks = chunk_text(text, max_length=15, overlap=5)
        # Expected:
        # "Hello world! Th" (0-15)
        # "d! This is a te" (10-25)
        # " a test string." (20-35)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], text[0:15])
        self.assertEqual(chunks[1], text[10:25])
        self.assertEqual(chunks[2], text[20:35])

    def test_extract_text_txt(self):
        content = b"Simple text"
        text = extract_text(content, "text/plain")
        self.assertEqual(text, "Simple text")

    def test_extract_text_csv(self):
        content = b"col1,col2\nval1,val2"
        text = extract_text(content, "text/csv")
        self.assertEqual(text, "col1, col2\nval1, val2")

    def test_extract_text_unsupported(self):
        with self.assertRaises(ValueError):
            extract_text(b"data", "application/pdf")

    @patch("app.services.document_processor.get_storage")
    def test_process_single_document_success(self, mock_get_storage):
        # Create KB and Document
        res = self.client.post("/api/v1/knowledge-bases", json={"name": "Upload KB"}, headers=self.auth(self.user1, self.tenant1))
        kb_id = res.json()["id"]

        doc = KnowledgeDocument(
            tenant_id=self.tenant1.id,
            knowledge_base_id=uuid.UUID(kb_id),
            title="test.txt",
            source_type="file",
            processing_status="pending",
            mime_type="text/plain",
            storage_key="dummy_key"
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        
        mock_storage = mock_get_storage.return_value
        mock_storage.iter_chunks.return_value = [b"Chunk 1 ", b"Chunk 2"]

        res = process_single_document(self.db, doc.id)
        self.assertEqual(res, "success")

        # Verify DB changes
        self.db.refresh(doc)
        self.assertEqual(doc.processing_status, "ready")
        self.assertIsNone(doc.error_summary)

        # Verify chunks
        chunks = self.db.query(KnowledgeDocumentChunk).filter_by(document_id=doc.id).all()
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text_content, "Chunk 1 Chunk 2")
        self.assertEqual(chunks[0].tenant_id, self.tenant1.id)

    @patch("app.services.document_processor.get_storage")
    def test_process_single_document_empty(self, mock_get_storage):
        # Create KB and Document
        res = self.client.post("/api/v1/knowledge-bases", json={"name": "Empty KB"}, headers=self.auth(self.user1, self.tenant1))
        kb_id = res.json()["id"]

        doc = KnowledgeDocument(
            tenant_id=self.tenant1.id,
            knowledge_base_id=uuid.UUID(kb_id),
            title="empty.txt",
            source_type="file",
            processing_status="pending",
            mime_type="text/plain",
            storage_key="empty_key"
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        mock_storage = mock_get_storage.return_value
        mock_storage.iter_chunks.return_value = [b"   "]

        res = process_single_document(self.db, doc.id)
        self.assertEqual(res, "failed")
        
        self.db.refresh(doc)
        self.assertEqual(doc.processing_status, "failed")
        self.assertIn("empty text", doc.error_summary.lower())

    @patch("app.services.document_processor.get_storage")
    def test_process_single_document_too_large(self, mock_get_storage):
        # Create KB and Document
        res = self.client.post("/api/v1/knowledge-bases", json={"name": "Large KB"}, headers=self.auth(self.user1, self.tenant1))
        kb_id = res.json()["id"]

        doc = KnowledgeDocument(
            tenant_id=self.tenant1.id,
            knowledge_base_id=uuid.UUID(kb_id),
            title="large.txt",
            source_type="file",
            processing_status="pending",
            mime_type="text/plain",
            storage_key="large_key"
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        mock_storage = mock_get_storage.return_value
        # return chunk generator of >30MB
        def chunk_gen():
            yield b"a" * (31 * 1024 * 1024)
        mock_storage.iter_chunks.return_value = chunk_gen()

        res = process_single_document(self.db, doc.id)
        self.assertEqual(res, "failed")
        
        self.db.refresh(doc)
        self.assertEqual(doc.processing_status, "failed")
        self.assertIn("excessively large", doc.error_summary)
