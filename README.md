# RaptoreumPay

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.13-blue)](https://www.python.org)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D24.0.0-green)](https://nodejs.org)
[![Database](https://img.shields.io/badge/database-MySQL-orange)](https://www.mysql.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

RaptoreumPay is a high-performance, non-custodial SaaS-style payment processor for **Raptoreum (RTM)**. By integrating directly with your private Raptoreum Core node, merchants can accept payments directly to their own wallets with zero third-party custody, zero middleman fees, and complete transaction privacy.

---

## 📖 System Documentation

To help you understand, deploy, and secure the system, a detailed documentation suite is available in the [docs/](file:///E:/RTM-Scripts/rtm-payservice/docs) folder:

* **[System Architecture](file:///E:/RTM-Scripts/rtm-payservice/docs/architecture.md)**: Explore the core components, database design, and non-custodial transaction sequence.
* **[API Reference](file:///E:/RTM-Scripts/rtm-payservice/docs/api.md)**: Specifications for invoice creation, merchant registration, webhook payloads, and admin tasks.
* **[Deployment Guide](file:///E:/RTM-Scripts/rtm-payservice/docs/deployment.md)**: Step-by-step instructions for MySQL installation, Systemd unit files, and Nginx reverse proxy with SSL.
* **[Security Policy](file:///E:/RTM-Scripts/rtm-payservice/SECURITY.md)**: Review our security policy, vulnerability reporting guidelines, and production hardening recommendations.
* **[Production Audit Report](file:///E:/RTM-Scripts/rtm-payservice/docs/audit_report.md)**: Comprehensive threat assessment covering CORS, webhooks, rate limits, and risk mitigations.

---

## ✨ Features

* **Non-Custodial Architecture**: Customers pay directly to merchant-controlled addresses. Funds never transit through a proxy wallet.
* **Database Backend**: Powered by **MySQL** for high concurrency, pool-recycled connections, and atomic operations.
* **Robust Address Generator**: Automatically creates and locks a unique single-use receiving address per invoice to guarantee invoice tracking.
* **Market Exchange Integration**: Connects with CoinGecko API to convert USD billing requests into RTM values dynamically.
* **Modern Developer Sandbox**: Interactive `/static/checkout-example.html` checkout simulator displaying developer logs and payment status tracking.
* **Self-Contained UI Widget**: Scoped, responsive CSS-styled payment widget embedded in a single script tag—fully independent of external CSS frameworks.
* **Webhook Notifications**: Emits immediate POST webhook alerts to merchant endpoints upon payment confirmation.

---

## 🛠️ Requirements

* **Python**: `3.10` up to `3.13` (Precompiled binary wheels for packages require Python <= 3.13)
* **Node.js**: Minimum `24.0.0` (For frontend asset linting, testing, and Prettier formatting)
* **Database**: MySQL `8.0+`
* **Daemon**: Running Raptoreum Core node (`raptoreumd`) with RPC activated.

---

## 🚀 Quick Start

### 1. Configure the Raptoreum Daemon
Enable RPC commands and optionally ZeroMQ event streaming inside your `raptoreum.conf` file:
```ini
server=1
rpcuser=your_rpc_username
rpcpassword=your_secure_rpc_password_999
rpcallowip=127.0.0.1
rpcbind=127.0.0.1
rpcport=8766

# Enable ZeroMQ publisher for transaction hashes (Phase 3 Event Streaming)
zmqpubhashtx=tcp://127.0.0.1:28332
```

### 2. Environment Configuration
Clone the repository and set up your local environment file:
```bash
cp .env.example .env
```
Edit `.env` to include your MySQL credentials, admin dashboard secrets, Raptoreum RPC details, and ZMQ configuration:
```env
# ZeroMQ Integration (set to True to enable instant unconfirmed payment detection)
ZMQ_ENABLED=True
ZMQ_HOST=127.0.0.1
ZMQ_PORT=28332
```

### 3. Install Dependencies
Set up your virtual environment and install backend requirements:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

Install Node formatting tools:
```bash
npm install
```

### 4. Run Database Migrations
Initialize or upgrade the MySQL database schema using Alembic:
```bash
alembic upgrade head
```

### 5. Format Static Assets
```bash
npm run format
```

### 6. Launch the Server
```bash
uvicorn app.main:app --reload
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to view the interactive API swagger. Open [http://localhost:8000/static/checkout-example.html](http://localhost:8000/static/checkout-example.html) to interact with the developer sandbox dashboard, or open [http://localhost:8000/static/dashboard.html](http://localhost:8000/static/dashboard.html) to manage your merchant account metrics and key settings.

---

## 🔌 Embedded Widget Integration

To display the payment widget on your store site, embed the container element and configure the initialization script:

```html
<!-- Payment Widget Target -->
<div id="rtm-checkout" 
     data-invoice-id="your_invoice_uuid"
     data-api-url="https://pay.yourdomain.com"
     data-theme="dark"> <!-- "light", "dark", or "system" -->
</div>

<!-- QR Code and Widget Script dependencies -->
<script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js"></script>
<script src="https://pay.yourdomain.com/static/widget.js"></script>

<script>
  RTMWidget.init({
    container: "rtm-checkout"
  });
</script>
```

---

## 🔒 Webhook Verification (HMAC-SHA256)

For production security, merchants should verify that incoming webhook payloads originate from the payment processor. Every webhook request includes two headers:
* `X-RTM-Signature`: Hex-encoded HMAC-SHA256 signature.
* `X-RTM-Timestamp`: UNIX timestamp string.

### Python Verification Example
```python
import hmac
import hashlib
import json

def verify_webhook(payload_bytes: bytes, api_key: str, signature_header: str, timestamp_header: str) -> bool:
    # 1. Prevent replay attacks by checking timestamp age (e.g., max 5 minutes)
    import time
    if abs(int(time.time()) - int(timestamp_header)) > 300:
        return False
    
    # 2. Re-create the signed message format exactly
    signed_payload = f"{timestamp_header}.".encode('utf-8') + payload_bytes
    
    # 3. Compute and compare HMAC
    computed = hmac.new(
        api_key.encode('utf-8'),
        signed_payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed, signature_header)
```

---

## 🗺️ System Roadmap

Our development strategy outlines immediate security upgrades, administrative UI enhancements, and scaling optimizations:

### 🚀 Phase 1: Security Hardening (Completed ✅)
* **HMAC-SHA256 Webhook Signatures**: [Completed] Webhooks are signed using the merchant's API Key and a timestamp to guarantee message authenticity and protect against replay attacks.
* **Pricing Cache Layer**: [Completed] Implemented a thread-safe local cache (5-minute TTL) with an expired cache fallback system to ensure uninterrupted service if CoinGecko goes offline.
* **RPC Connection Timeout Protections**: [Completed] Constructed an RPC retry method with incremental backoff (3 attempts) to improve resilience against transient network anomalies and daemon restarts.

### 📊 Phase 2: Administrative Enhancements (Completed ✅)
* **Merchant Dashboard UI**: [Completed] Developed a premium, responsive merchant dashboard (`static/dashboard.html`) to monitor transaction metrics, active invoices, and configuration details.
* **Interactive Invoice Generator**: [Completed] Built an admin-level generator interface directly inside the dashboard to manually create payment links and embed codes.
* **Export Utilities**: [Completed] Integrated backend export streams allowing merchants to instantly download billing history in JSON and CSV formats.

### ⚡ Phase 3: Scaling & Event Streaming (Completed ✅)
* **ZeroMQ (ZMQ) Integration**: [Completed] Constructed a ZeroMQ listener daemon thread subscribing to `hashtx` blocks to receive instant blockchain payment notifications without polling.
* **WebSockets Gateway**: [Completed] Developed real-time WebSocket status endpoints (`/api/payment/{id}/ws`) and updated the checkout widget to use hybrid WebSocket connections with a REST poll fallback.
* **Database Migration Engine**: [Completed] Integrated **Alembic** to manage automatic database schema migrations.

### 🛡️ Phase 4: Advanced Production Enhancements (Completed ✅)
* **Rate Limiting & Anti-Spam**: [Completed] Integrated rate limiting (using `slowapi`) to protect key endpoints from API spam, keypool exhaustion, and brute-force registration.
* **Watch-Only HD Wallet Derivation**: [Completed] Developed offline RTM legacy address derivation from an Account Extended Public Key (`xpub`) using the `bip-utils` library, allowing nodes to run securely with zero private keys stored on-server.
* **Reorg & Double-Spend Defenses**: [Completed] Separated mempool detection (`"detected"`) from confirmed finalization (`"paid"`) depending on customizable confirmation block depth targets.
* **Database Webhook Queue & DLQ**: [Completed] Implemented a database-backed webhook queue with exponential retry backoff and routing of failed notifications to a Dead Letter Queue (DLQ).
* **Redis Caching & Pub/Sub**: [Completed] Configured Redis caching for price oracles and Redis Pub/Sub coordination to scale the WebSocket gateway across multiple API instances.
* **Database Pagination**: [Completed] Implemented limit/offset pagination and streaming CSV exports to prevent server memory bloat.