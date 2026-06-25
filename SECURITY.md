# Security Policy & Guidelines (SECURITY.md)

RaptoreumPay is a non-custodial payment processor designed to route funds directly to merchant wallets. Ensuring the security of payment operations, API keys, and private infrastructure is of paramount importance.

## Supported Versions

Only the latest release version is actively supported with security updates.

| Version | Supported |
| ------- | --------- |
| 1.x.x   | Yes       |
| < 1.0.0 | No        |

## Reporting a Vulnerability

We appreciate responsible disclosure. If you discover a security vulnerability in this project, please follow these steps:

1. **Do Not File Public Issues**: Do not report security vulnerabilities via public GitHub issues.
2. **Email Disclosure**: Send a detailed description of the vulnerability, including step-by-step reproduction instructions and code examples, to: **security@yourdomain.com** (replace with your secure reporting channel).
3. **Response Timeline**: The security team will acknowledge receipt of your email within 24 hours, and provide a preliminary response or patch proposal within 72 hours.
4. **Coordinated Disclosure**: We ask you to wait until we release an official security patch before disclosing the vulnerability publicly to minimize risk to active merchants.

---

## Production Security Best Practices

To transition this system into production, you MUST implement the following security measures:

### 1. Mandatory TLS/HTTPS
Never run this payment processor in production over unencrypted HTTP.
- Enforce SSL/TLS certificates via Nginx, Apache, or Cloudflare.
- Configure HTTP Strict Transport Security (HSTS) headers.
- Since payments poll API status, unencrypted traffic could expose invoice IDs or lead to MITM invoice status spoofing.

### 2. Admin Credentials Overhaul
The application configures a default admin dashboard username (`admin`) and password (`change_me`).
- Always override these default credentials using environment variables:
  ```env
  ADMIN_USERNAME=your_secure_admin_user
  ADMIN_PASSWORD=your_super_strong_random_password_999!
  ```
- Change these values immediately upon deployment.

### 3. Database Least Privilege (MySQL)
When setting up MySQL for production:
- Create a dedicated database user for `raptoreumpay` (do NOT run as root).
- Grant only the necessary privileges required for standard operations:
  ```sql
  CREATE USER 'rtm_pay_user'@'localhost' IDENTIFIED BY 'secure_password';
  GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, ALTER ON raptoreumpay.* TO 'rtm_pay_user'@'localhost';
  FLUSH PRIVILEGES;
  ```

### 4. Protecting Raptoreum Core RPC Credentials
The payment processor relies on direct RPC calls to a running Raptoreum Core node.
- **Isolate the RPC Port**: Never expose the Raptoreum Core RPC port (default `8766`) to the public internet. It should only listen on `127.0.0.1` or be restricted via firewall rules (`iptables` / Security Groups) to the payment processor's IP address.
- **Isolate the ZMQ Port**: If ZeroMQ integration is enabled, ensure the ZMQ port (default `28332`) is isolated in the same manner. Restrict connection listening to localhost or the private network IP of the payment processor. Since ZeroMQ feeds do not use default authentication, exposing the port publicly poses a service spam risk.
- **Use Strong RPC Passwords**: Core wallet nodes can authorize transactions (such as sending change or consolidating UTXOs). Use highly complex, randomly generated RPC usernames and passwords.

### 5. API Key & CORS Management
- By default, the FastAPI application uses a CORS wildcard (`allow_origins=["*"]`) to allow the client-side checkout widget to communicate with the payment server from any domain.
- While required for flexible widget embeds, restrict `/api/merchant/*` routes or implement origin checks to prevent unauthorized registrations if public registration is not desired.
- Keep merchant API keys confidential. Store them server-side; they should never be exposed in client-side script code.
- **API Key Rotation**: If a merchant suspects that their API Key has been compromised, they should immediately perform a key rotation via the settings panel in the Merchant Dashboard (`/static/dashboard.html`). This immediately deactivates the old key in the database and generates a secure new replacement, stopping any unauthorized invoice creation.

### 6. Webhook Authenticity & Webhook Signatures
Webhooks notify merchant systems when a payment is received. If a malicious third party sends spoofed webhook payloads to the merchant, they could trick the merchant into shipping goods without paying.
- **HMAC-SHA256 Webhook Signatures (Active)**: In version 1.0.0+, webhooks are automatically signed using HMAC-SHA256 with the merchant's secret API key. The signature is transmitted in the `X-RTM-Signature` header, along with a `X-RTM-Timestamp` header. This prevents webhook tampering and replay attacks. Merchants must verify these signatures on their endpoints.
- **IP Whitelisting**: Recommend merchants whitelist the static IP of your payment processor server.

### 7. Watch-Only HD Key Security
- If offline HD wallet derivation is configured, keep the merchant's Master Private Key (`xprv`) completely offline (e.g. on a hardware wallet or secure offline backup).
- Only register the Master Public Key (`xpub`) in the database. An `xpub` allows child public key derivation without private key access, protecting the wallet balance from theft even if the database is compromised.

### 8. API Spam & Keypool Exhaustion Protection
- Endpoints that perform database writes (invoice creation, merchant registration) are protected by a rate limiter (`slowapi`).
- Keep rate limits active (customizable in settings) to prevent keypool exhaustion on the core node and database bloat from brute-force scripts.
