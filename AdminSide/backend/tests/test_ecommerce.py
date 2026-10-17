import uuid
import datetime
from sqlalchemy import select

from tests.base import DatabaseTestCase
from app.models.ecommerce import OrderStatus
from app.models.contact import Contact

class TestEcommerce(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.tenant_a = self.make_tenant("Tenant A")
        self.tenant_b = self.make_tenant("Tenant B")
        self.admin_a = self.make_member(self.tenant_a, "ADMIN")
        self.admin_b = self.make_member(self.tenant_b, "ADMIN")

        self.contact = Contact(tenant_id=self.tenant_a.id, phone_number="123")
        self.db.add(self.contact)
        self.db.commit()

    def test_ecommerce_overview_empty(self):
        res = self.client.get("/api/v1/ecommerce/overview", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_products"], 0)
        self.assertEqual(data["total_orders"], 0)
        self.assertEqual(data["pending_orders"], 0)
        self.assertEqual(data["total_revenue"], 0.0)

    def test_create_and_get_product(self):
        product_data = {
            "name": "Test Product",
            "sku": "TP-01",
            "price": 29.99,
            "currency": "USD"
        }
        res = self.client.post("/api/v1/ecommerce/products", json=product_data, headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        product = res.json()
        self.assertEqual(product["name"], "Test Product")
        
        # Get List
        res = self.client.get("/api/v1/ecommerce/products", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["id"], product["id"])
        
        # Get Single
        res = self.client.get(f"/api/v1/ecommerce/products/{product['id']}", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], product["id"])

    def test_update_and_delete_product(self):
        product_data = {"name": "Product To Update", "price": 10.0}
        res = self.client.post("/api/v1/ecommerce/products", json=product_data, headers=self.auth(self.admin_a, self.tenant_a))
        product_id = res.json()["id"]
        
        # Update
        update_data = {"price": 15.0}
        res = self.client.patch(f"/api/v1/ecommerce/products/{product_id}", json=update_data, headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["price"], 15.0)
        
        # Delete
        res = self.client.delete(f"/api/v1/ecommerce/products/{product_id}", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        
        # Verify deleted
        res = self.client.get(f"/api/v1/ecommerce/products/{product_id}", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 404)

    def test_create_and_get_order(self):
        product_data = {"name": "Order Product", "price": 10.0}
        product_res = self.client.post("/api/v1/ecommerce/products", json=product_data, headers=self.auth(self.admin_a, self.tenant_a))
        product_id = product_res.json()["id"]

        order_data = {
            "contact_id": str(self.contact.id),
            "order_number": f"ORD-{uuid.uuid4().hex[:6]}",
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 2
                }
            ]
        }
        res = self.client.post("/api/v1/ecommerce/orders", json=order_data, headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        order = res.json()
        self.assertEqual(order["order_number"], order_data["order_number"])
        self.assertEqual(len(order["items"]), 1)
        
        # Get List
        res = self.client.get("/api/v1/ecommerce/orders", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["total"], 0)
        self.assertTrue(any(o["id"] == order["id"] for o in data["items"]))

    def test_update_order_status(self):
        order_data = {
            "order_number": f"ORD-{uuid.uuid4().hex[:6]}",
            "items": []
        }
        res = self.client.post("/api/v1/ecommerce/orders", json=order_data, headers=self.auth(self.admin_a, self.tenant_a))
        order_id = res.json()["id"]
        
        # Invalid transition: PENDING -> DELIVERED
        res = self.client.patch(f"/api/v1/ecommerce/orders/{order_id}", json={"status": "delivered"}, headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid transition", res.json()["detail"])

        # Valid transitions: PENDING -> PROCESSING -> SHIPPED -> DELIVERED
        for valid_status in ["processing", "shipped", "delivered"]:
            res = self.client.patch(f"/api/v1/ecommerce/orders/{order_id}", json={"status": valid_status}, headers=self.auth(self.admin_a, self.tenant_a))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["status"], valid_status)

        # Invalid string entirely (Pydantic check)
        res = self.client.patch(f"/api/v1/ecommerce/orders/{order_id}", json={"status": "magic_status"}, headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 422)

    def test_tenant_isolation(self):
        # Create product in tenant A
        res = self.client.post("/api/v1/ecommerce/products", json={"name": "A Product", "price": 1.0}, headers=self.auth(self.admin_a, self.tenant_a))
        product_id = res.json()["id"]
        
        # Tenant B tries to read
        res = self.client.get(f"/api/v1/ecommerce/products/{product_id}", headers=self.auth(self.admin_b, self.tenant_b))
        self.assertEqual(res.status_code, 404)
        
        # Tenant B tries to update
        res = self.client.patch(f"/api/v1/ecommerce/products/{product_id}", json={"name": "B Name"}, headers=self.auth(self.admin_b, self.tenant_b))
        self.assertEqual(res.status_code, 404)

        # Tenant B tries to delete
        res = self.client.delete(f"/api/v1/ecommerce/products/{product_id}", headers=self.auth(self.admin_b, self.tenant_b))
        self.assertEqual(res.status_code, 404)
        
        # Test cross-tenant product in order creation
        order_cross = {
            "order_number": f"ORD-{uuid.uuid4().hex[:6]}",
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 1
                }
            ]
        }
        res = self.client.post("/api/v1/ecommerce/orders", json=order_cross, headers=self.auth(self.admin_b, self.tenant_b))
        self.assertEqual(res.status_code, 400)
        self.assertIn("not found or does not belong", res.json()["detail"])

        # Test cross-tenant contact in order creation
        order_cross_contact = {
            "contact_id": str(self.contact.id), # Belongs to tenant A
            "order_number": f"ORD-{uuid.uuid4().hex[:6]}",
            "items": []
        }
        res = self.client.post("/api/v1/ecommerce/orders", json=order_cross_contact, headers=self.auth(self.admin_b, self.tenant_b))
        self.assertEqual(res.status_code, 400)
        self.assertIn("Contact not found", res.json()["detail"])
