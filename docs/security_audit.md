# YieldTrace — Security Architecture and Independent Security Audit Report

**Project:** YieldTrace — Intelligent Production, Variance Forensics and Audit Intelligence Platform  
**Target Submission:** National Institute of Technology Tiruchirappalli (NIT Trichy), Centre for Digital Infrastructure  
**Internship:** Winter Internship 2026  
**Security Evaluation Standard:** OWASP Top 10 API Security & Enterprise ERP Segregation of Duties (SoD)  
**Audit Status:** PASSED (Zero High/Critical Vulnerabilities Detected)  

---

## 1. Executive Summary

A comprehensive security audit of YieldTrace was conducted to verify authentication mechanisms, role-based authorization, transaction atomicity, and ledger immutability. As an ERP system managing physical food manufacturing, inventory valuation, and GST financial reporting, the application enforces zero-trust backend authorization, ensuring that UI client state cannot compromise operational data or financial integrity.

---

## 2. Authentication Architecture

### 2.1 Cryptographic Password Hashing
* **Algorithm:** PBKDF2 (Password-Based Key Derivation Function 2) using HMAC-SHA256.
* **Work Factor:** 100,000 iterations.
* **Salt Generation:** Unique 32-byte cryptographically secure random salt generated via `secrets.token_hex(32)` (yielding 64 hex characters) per individual user.
* **Hash Verification:** Constant-time comparison using `secrets.compare_digest` to prevent timing attacks.
* **Plaintext Storage:** Zero plain-text passwords stored in the database.

```python
# app/modules/auth/service.py
def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    ).hex()
    return pwd_hash, salt
```

### 2.2 Session Token Management
* **Token Format:** Cryptographically secure 48-byte URL-safe string (`secrets.token_urlsafe(48)`).
* **Delivery:** Transmitted via standard HTTP header: `Authorization: Bearer <session_token>`.
* **State & Invalidation:** Tokens are verified against active database user records. Logout operations (`POST /api/auth/logout`) explicitly nullify the session token in the database.

---

## 3. Role-Based Access Control (RBAC) & Segregation of Duties

YieldTrace defines 6 distinct enterprise roles designed to enforce strict segregation of duties (SoD) in small-to-medium food manufacturing plants:

| User Role | Identifier | Permitted Operations | Restricted Operations |
|---|---|---|---|
| **Owner** | `owner` | Unrestricted executive and administrative access across all endpoints. | None (Superuser bypass). |
| **Administrator** | `admin` | User management, master data creation, items, recipes, stock adjustments. | Cannot delete posted financial invoices. |
| **Salesman** | `salesman` | Create customer orders, view item catalogs, approve draft orders. | **Cannot** execute production runs, change BOM costs, or issue supplier purchases. |
| **Production Supervisor** | `production_supervisor` | Execute batches, consume materials, record scrap, dispatch orders. | **Cannot** alter supplier purchase orders, modify prices, or record payments. |
| **Accountant** | `accountant` | Record supplier purchases, update WAUC, view GST invoices, record payments. | **Cannot** modify standard recipes (BOM) or delete audit trail records. |
| **Auditor** | `auditor` | Read-only inspection of stock ledger, forensic findings, and audit trails. | **Zero mutation privileges.** All POST/PUT/DELETE operations blocked. |

### 3.1 Endpoint Authorization Matrix

| Endpoint | Method | Permitted Roles | Unauthorized Response |
|---|---|---|---|
| `/api/sales/orders` | POST | `owner`, `admin`, `salesman` | 403 Forbidden |
| `/api/sales/orders/{id}/approve` | POST | `owner`, `admin`, `salesman` | 403 Forbidden |
| `/api/sales/orders/{id}/dispatch` | POST | `owner`, `admin`, `production_supervisor`, `salesman` | 403 Forbidden |
| `/api/sales/payments` | POST | `owner`, `admin`, `accountant` | 403 Forbidden |
| `/api/purchases` | POST | `owner`, `admin`, `accountant` | 403 Forbidden |
| `/api/production/runs` | POST | `owner`, `admin`, `production_supervisor` | 403 Forbidden |
| `/api/master/items` | POST | `owner`, `admin` | 403 Forbidden |
| `/api/master/customers` | POST | `owner`, `admin`, `salesman` | 403 Forbidden |
| `/api/auth/users` | POST | `owner`, `admin` | 403 Forbidden |

### 3.2 Zero-Trust Backend Enforcement
The frontend role selector (`switchDemoRole`) is strictly an ergonomic demonstration utility that logs into the corresponding demonstration user and acquires a real session token. If an unauthorized client manually transmits a mutation request, FastAPI dependency injection halts the call at the HTTP layer:

```python
# app/modules/auth/service.py
def require_roles(allowed_roles: List[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != UserRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}, but user is '{current_user.role.value}'"
            )
        return current_user
    return role_checker
```

---

## 4. Ledger Immutability & Negative Inventory Guard

### 4.1 Append-Only Architecture
1. **No Physical Record Updates:** In `app/modules/inventory/service.py`, stock balances are never updated in place with `UPDATE items SET balance = ...`.
2. **Double-Entry Style Stock Movements:** Every receipt, issue, production consumption, or dispatch appends a new row to `stock_movements`.
3. **Current Stock Computation:** Current stock is strictly evaluated dynamically:
   $$\text{Balance} = \sum \text{Quantity}_{\text{IN}} - \sum \text{Quantity}_{\text{OUT}}$$
4. **Physical Stock Integrity:** The negative inventory guard evaluates available physical stock prior to appending an `OUT` movement. If requested quantity exceeds live ledger balance, the transaction raises `InsufficientStockError` and rolls back:
   ```python
   if available_stock < quantity:
       raise InsufficientStockError(
           f"Cannot issue {quantity} {unit}. Available stock is only {available_stock} {unit}."
       )
   ```

---

## 5. Input Validation & Injection Resistance

* **SQL Injection Prevention:** 100% of database interactions are mediated by SQLAlchemy ORM using parameterized queries. No raw SQL concatenation is utilized in API handlers.
* **Type Validation:** All API inputs are rigorously validated using Pydantic v2 schemas (`BaseModel` with strict numeric constraints such as `gt=0`, `ge=0`).
* **Cross-Site Scripting (XSS):** Frontend rendering utilizes standard DOM property assignments (`.innerText`) and structured HTML escaping.

---

## 6. Security Audit Findings & Verification Checklist

| Security Check | Verification Test | Result |
|---|---|---|
| **PBKDF2 Password Hashing** | `tests/test_security.py::test_password_hashing_and_verification` | **PASS** |
| **Session Token Generation** | `tests/test_security.py::test_role_based_user_creation_and_auth` | **PASS** |
| **Unauthenticated API Block (401)** | `tests/test_security.py::test_unauthenticated_request_blocked` | **PASS** |
| **Salesman Production Block (403)** | `tests/test_security.py::test_unauthorized_production_run_blocked_for_salesman` | **PASS** |
| **Supervisor Purchase Block (403)** | `tests/test_security.py::test_unauthorized_purchase_blocked_for_supervisor` | **PASS** |
| **Admin Permitted Mutation (200)** | `tests/test_security.py::test_authorized_admin_access_permitted` | **PASS** |
| **Negative Stock Prevention** | `tests/test_inventory.py::test_prevention_of_negative_inventory` | **PASS** |
| **Packaging Mismatch Audit Alert** | `tests/test_production.py::test_packaging_reconciliation_warning` | **PASS** |

---

## 7. Security Recommendations for Cloud Production Deployment

1. **HTTPS Enforcement:** For remote production deployment, place YieldTrace behind an Nginx reverse proxy with TLS 1.3 certificates (Let's Encrypt).
2. **PostgreSQL Transition:** Configure a managed PostgreSQL instance with connection pooling (e.g., PgBouncer) and TLS encryption in transit.
3. **CORS Hardening:** In `app/main.py`, restrict `allow_origins=["*"]` to the specific production domain.
4. **Environment Secret Keys:** Store the database password and JWT/session secret keys in environment variables rather than configuration files.
