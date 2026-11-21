"""
Unit tests for Authentication, Role-Based Access Control, and Security.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models import UserRole
from app.modules.auth.service import AuthService, verify_password, hash_password


@pytest.fixture
def client(db_session):
    """Provide a TestClient with database session overridden to the test DB."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_password_hashing_and_verification(db_session):
    """Verify PBKDF2-HMAC-SHA256 password hashing with cryptographic salt."""
    raw_pass = "SecurePass@2026"
    pwd_hash, salt = hash_password(raw_pass)

    assert pwd_hash != raw_pass
    assert len(salt) == 64  # 32 bytes hex
    assert verify_password(raw_pass, pwd_hash, salt) is True
    assert verify_password("WrongPassword", pwd_hash, salt) is False


def test_role_based_user_creation_and_auth(db_session):
    """Verify user registration, roles, and session token generation."""
    auth = AuthService(db_session)
    user = auth.register_user(
        username="auditor_test",
        email="audit_test@yieldtrace.local",
        password="AuditPassword#1",
        role=UserRole.AUDITOR,
        full_name="Karthik Auditor"
    )

    assert user.id is not None
    assert user.role == UserRole.AUDITOR

    # Authenticate
    authenticated = auth.authenticate("auditor_test", "AuditPassword#1")
    assert authenticated is not None
    assert authenticated.session_token is not None
    assert len(authenticated.session_token) > 20

    # Test invalid password
    failed = auth.authenticate("auditor_test", "InvalidPass")
    assert failed is None


def test_unauthenticated_request_blocked(client):
    """Verify protected mutation endpoints reject unauthenticated requests with HTTP 401."""
    res = client.post("/api/production/runs", json={"run_number": "RUN-TEST", "bom_id": 1, "planned_batches": 1.0, "actual_consumptions": [], "good_packets_produced": 100})
    assert res.status_code == 401
    assert "Authentication token required" in res.json()["detail"]


def test_unauthorized_production_run_blocked_for_salesman(client, canonical_benchmark_setup):
    """Verify salesman role cannot trigger production execution (HTTP 403 Forbidden)."""
    db = canonical_benchmark_setup
    auth = AuthService(db)
    salesman = auth.authenticate("sales", "Password@123")
    assert salesman is not None

    headers = {"Authorization": f"Bearer {salesman.session_token}"}
    payload = {
        "run_number": "RUN-UNAUTHORIZED-01",
        "bom_id": 1,
        "planned_batches": 1.0,
        "actual_consumptions": [{"item_id": 1, "actual_quantity": 40.0}],
        "good_packets_produced": 188.0,
        "damaged_packets": 6.0,
        "cartons_used": 9.0
    }
    res = client.post("/api/production/runs", json=payload, headers=headers)
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_unauthorized_purchase_blocked_for_supervisor(client, canonical_benchmark_setup):
    """Verify production supervisor role cannot record supplier purchases (HTTP 403 Forbidden)."""
    db = canonical_benchmark_setup
    auth = AuthService(db)
    prod = auth.authenticate("prod", "Password@123")
    assert prod is not None

    headers = {"Authorization": f"Bearer {prod.session_token}"}
    payload = {
        "invoice_no": "INV-ILLEGAL-01",
        "supplier_id": 1,
        "lines": [{"item_id": 1, "quantity": 100.0, "unit_price": 40.0}]
    }
    res = client.post("/api/purchases", json=payload, headers=headers)
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_authorized_admin_access_permitted(client, canonical_benchmark_setup):
    """Verify admin role is authorized to create orders."""
    db = canonical_benchmark_setup
    from app.models import Customer, Item
    cust = db.query(Customer).first()
    item = db.query(Item).filter(Item.code == "FG-MURUKKU-200G").first()
    auth = AuthService(db)
    admin = auth.authenticate("admin", "Password@123")
    assert admin is not None

    headers = {"Authorization": f"Bearer {admin.session_token}"}
    payload = {
        "order_number": "SO-AUTH-001",
        "customer_id": cust.id,
        "lines": [{"item_id": item.id, "ordered_quantity": 10.0, "unit_price": 50.0}]
    }
    res = client.post("/api/sales/orders", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["order_number"] == "SO-AUTH-001"


