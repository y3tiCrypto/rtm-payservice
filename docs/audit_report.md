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
* **Status**: **HIGH RISK (Payment Verification)**
* **Finding**: Webhooks (`app/services/polling.py`) transmit JSON payloads over plain HTTP POST to the merchant URL without signatures.
* **Threat**: If a third party figures out a merchant's webhook URL, they can send a forged `payment.confirmed` payload to trick the merchant into releasing products without paying.
* **Mitigation**:
  1. Introduce Webhook Signatures. Calculate an HMAC using SHA256 over the request body with a shared secret key:
     ```python
     signature = hmac.new(secret_key, request_body, hashlib.sha256).hexdigest()
     ```
  2. Append the signature as a header (e.g., `X-RTM-Signature`).
  3. Instruct merchants to check this signature before fulfilling orders.

---

## 2. Operational & Infrastructure Audit

### 2.1 CoinGecko Pricing Dependency
* **Status**: **LOW-MEDIUM RISK (External Dependency)**
* **Finding**: The payment system converts USD to RTM using CoinGecko's public endpoint (`app/services/price.py`).
* **Threat**: CoinGecko's free public endpoint has strict rate limits and is prone to temporary outages. If CoinGecko is down, invoice creation with `amount_usd` returns a `0.0` exchange rate, causing invoice creation to fail (HTTP 503).
* **Mitigation**:
  1. Implement pricing caching. Store the RTM exchange rate in database/memory cache and refresh it every 5 minutes instead of querying CoinGecko for every invoice.
  2. Configure secondary fallback price APIs (e.g., Coinpaprika, TradeOgre, or Dex-Trade APIs).

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
| Webhook Security | **High** | Implement HMAC Webhook signatures. |
| Admin Basic Auth | **Medium** | Enforce TLS and rotate default credentials immediately. |
| CORS Control | **Medium** | Restrict origins for administrative routes. |
| Price Oracle | **Medium** | Implement a local pricing cache (5-minute TTL) to avoid API rate limits. |
| Scale limits | **Low** | If invoice volume exceeds 10,000 active concurrent invoices, migrate from polling to ZMQ. |
