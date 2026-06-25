# Production Readiness & Security Audit Report (audit_report.md)

This report details a complete security and operational audit of RaptoreumPay. It evaluates security vulnerabilities, operational constraints, database layers, and infrastructure concerns to assess readiness for production.

---

## 1. Security Architecture Audit

### 1.1 SQL Injection Risk
* **Status**: **PASS (Secured)**
* **Finding**: The database layer has been audited. There is no raw SQL string interpolation. All queries in the controllers (`app/routers/payment.py` and `app/routers/merchant.py`) and background worker (`app/services/polling.py`) utilize the **SQLAlchemy ORM expression language** (e.g., `db.query(Invoice).filter(Invoice.id == invoice_id).first()`).
* **Technical Detail**: SQLAlchemy compiles these expressions into parameterized SQL queries, making the application immune to SQL injection.

### 1.2 Admin Backup Route Authenticity
* **Status**: **MEDIUM RISK**
* **Finding**: The admin backup endpoint `/admin/backup` is protected using **HTTP Basic Authentication** (`verify_admin` via FastAPI's `HTTPBasic`).
* **Threat**: HTTP Basic Authentication transmits credentials in a Base64-encoded header, which is easily sniffed if TLS is not enforced.
* **Mitigation**:
  1. Mandatory TLS/HTTPS configuration in production.
  2. Implement an OAuth2 or API token-based administration layout for sensitive systems.
  3. Ensure the admin username/password are rotated out of the default credentials using environment variables.

### 1.3 CORS (Cross-Origin Resource Sharing) Policy
* **Status**: **MEDIUM RISK (Operational Necessity)**
* **Finding**: In `app/main.py`, CORS allows all origins: `allow_origins=["*"]`.
* **Technical Detail**: While this is necessary for the embeddable check-out widget to be fetched from any merchant website, it also allows arbitrary domains to hit merchant management endpoints if not properly segregated.
* **Mitigation**: Split routing rules in Nginx so that `/api/payment/...` remains public, but `/api/merchant/...` and `/admin/...` check for host headers or origin validation to prevent CSRF and unauthorized script executions.

### 1.4 Webhook Spoofing / Authenticity
* **Status**: **PASS (Mitigated)**
* **Finding**: Webhooks are automatically signed using the merchant's secret API key.
* **Mitigation**: Implemented HMAC-SHA256 signature calculations. The signature is computed over `timestamp + "." + json_payload` and sent in the `X-RTM-Signature` header, along with `X-RTM-Timestamp`. This completely mitigates webhook spoofing and replay attacks.

---

## 2. Operational & Infrastructure Audit

### 2.1 CoinGecko Pricing Dependency
* **Status**: **PASS (Mitigated)**
* **Finding**: System relies on CoinGecko for USD conversions.
* **Mitigation**: Implemented a thread-safe local pricing cache (5-minute TTL). In the event of a CoinGecko outage or rate limit block, the system automatically falls back to serving the last known good cached price, ensuring invoice creation continues to operate smoothly.

### 2.2 Blockchain Transaction Polling Loop
* **Status**: **PASS (Functional)**
* **Finding**: Payment detection is handled via a 30-second interval polling script (`app/services/polling.py`) querying `getreceivedbyaddress` via the Raptoreum RPC node.
* **Operational Constraint**: The current polling loop queries all pending invoices individually. If there are thousands of active pending invoices simultaneously, this will trigger thousands of RPC requests to the Raptoreum Core node every 30 seconds.
* **Mitigation**:
  1. Set a reasonable invoice duration (default is 45 minutes) to ensure expired invoices are cleaned up promptly.
  2. For massive scale, replace polling with **ZMQ (ZeroMQ)** integration. Raptoreum Core supports publishing block and transaction events (e.g., `-zmqpubrawtx` or `-zmqpubrawblock`) to instantly notify the payment backend on incoming blockchain transfers without polling.

---

## 3. Technology Stack Compliance

### 3.1 Node.js 24 Requirement
* **Status**: **PASS (Compliant)**
* **Finding**: The frontend package system has been locked to Node 24 minimum via `package.json` `"engines": { "node": ">=24.0.0" }`.
* **Verification**: Running `node --version` on the host machine confirms version `v24.12.0`.

### 3.2 Python 3.13 Compliance
* **Status**: **PASS (Compliant)**
* **Finding**: The server runs under Python 3.13, utilizing clean libraries.
* **Verification**: Code syntax check and library imports are fully functional.

---

## 4. Audit Summary & Action Items

| Item | Threat Level | Resolution |
| ---- | ------------ | ---------- |
| Webhook Security | **Mitigated (PASS)** | Webhooks are signed with HMAC-SHA256 and timestamps (v1.0.0+). |
| Admin Basic Auth | **Medium** | Enforce TLS and rotate default credentials immediately. |
| CORS Control | **Medium** | Restrict origins for administrative routes. |
| Price Oracle | **Mitigated (PASS)** | Thread-safe pricing cache with stale fallback (v1.0.0+) and Redis cache integration (v1.3.0+). |
| Key Compromise | **Mitigated (PASS)** | Merchant API Key rotation and dashboard control panel implemented (v1.1.0+). |
| Scale limits | **Mitigated (PASS)** | ZeroMQ transaction streaming and WebSockets gateway implemented (v1.2.0+) with Redis Pub/Sub horizontal scale (v1.3.0+). |
| API Spam / DOS | **Mitigated (PASS)** | API rate limiting using `slowapi` on write endpoints (v1.3.0+). |
| Node Key Theft | **Mitigated (PASS)** | Watch-only HD address derivation from merchant `xpub` (v1.3.0+). |
| Double Spend / Reorg | **Mitigated (PASS)** | Confirmation block depth validation before payment finalization (v1.3.0+). |
| Webhook Drops | **Mitigated (PASS)** | Database-backed webhook queue with exponential backoff retries and DLQ (v1.3.0+). |
| Memory Bloat | **Mitigated (PASS)** | Paginated invoice lists and chunked streaming CSV exports (v1.3.0+). |
