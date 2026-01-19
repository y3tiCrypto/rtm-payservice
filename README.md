# RaptoreumPay
Simple SaaS-style payment processor for Raptoreum (RTM). Merchants get paid directly to their own wallets – no custody, only network fees.  

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
3. Edit .env and fill in your values
4. Start the server
   uvicorn app.main:app --reload
5. Open http://localhost:8000/docs to see the interactive API documentation
6. Embed the payment widget on your website (see integration docs below)

## Example raptoreum.conf
```raptoreum.conf
server=1
rpcuser=youruser
rpcpassword=yourverystrongpassword123
rpcallowip=127.0.0.1
rpcbind=0.0.0.0
rpcport=8766
```

## Embed the Payment Widget
```html
<!-- RaptoreumPay Payment Widget -->
<div id="rtm-checkout" 
     data-invoice-id="inv_abc123"
     data-api-url="https://pay.yourdomain.com"
     data-theme="dark">   <!-- or "light" -->
</div>

<!-- Widget script -->
<script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js"></script>
<script src="https://pay.yourdomain.com/static/widget.js"></script>

<script>
  RTMWidget.init({
    container: "rtm-checkout",
    // optional overrides
    theme: "dark",          // "light" or "dark" – defaults to system preference
    pollingInterval: 30000  // ms
  });
</script>
```

## Security Warning
This is early MVP software – use with caution:

- Test everything on testnet first
- Use HTTPS in production
- Implement rate limiting
- Protect the admin backup interface properly
- Never expose your RPC credentials publicly