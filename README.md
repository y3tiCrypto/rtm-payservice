# RaptoreumPay MVP – Accept RTM Payments (Non-Custodial)

Simple SaaS-style payment processor for Raptoreum (RTM).  
Merchants get paid directly to their own wallets – no custody, only network fees.

Status: MVP – polling-based, SQLite, Bootstrap 5 widget with light/dark mode
<p align="center">
  <img src="https://img.shields.io/badge/Status-MVP-orange?style=for-the-badge" alt="Status: MVP">
</p>

## Features
- Create invoice via API (amount in RTM or fiat equivalent)
- Unique receive address per invoice
- Responsive checkout widget (simple <script> embed)
- Light / Dark mode support in the payment widget
- Real-time fiat conversion using CoinGecko
- Webhook notification when payment is received
- Basic admin backup UI (for debugging and tracking)
- Pure polling-based payment detection (no ZMQ)

## Requirements
- Python 3.10+
- Running Raptoreum Core node with RPC enabled
- .env file containing RPC credentials

## Quick Start

1. Clone the repository
2. Install dependencies
   pip install -r requirements.txt
3. Copy .env.example to .env and fill in your values
4. Start the server
   uvicorn app.main:app --reload
5. Open http://localhost:8000/docs to see the interactive API documentation
6. Embed the payment widget on your website (see integration docs below)

## Example raptoreum.conf (place in your node data directory)

server=1
rpcuser=youruser
rpcpassword=yourverystrongpassword123
rpcallowip=127.0.0.1
rpcbind=0.0.0.0
rpcport=8766

## Security Warning

This is early MVP software – use with caution:

- Test everything on testnet first
- Use HTTPS in production
- Implement rate limiting
- Protect the admin backup interface properly
- Never expose your RPC credentials publicly

Made for the Raptoreum community  
By Y3TI (@y3tiCrypto) 🦖🚀

Last updated: January 2026