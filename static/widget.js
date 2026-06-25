// RaptoreumPay Scoped Payment Widget - Self-contained & Production Ready
// Usage: <div id="rtm-checkout" data-invoice-id="..." data-api-url="..." data-theme="dark|light|system"></div>

(function () {
  if (window.RTMWidget) return; // prevent multiple loads

  const INJECTED_STYLE_ID = "rtm-widget-styles";

  // Scoped CSS styles for the payment widget
  const WIDGET_CSS = `
        .rtm-widget-card {
            font-family: 'Outfit', 'Inter', system-ui, -apple-system, sans-serif;
            max-width: 400px;
            margin: 0 auto;
            border-radius: 20px;
            padding: 28px;
            background: var(--rtm-card-bg);
            color: var(--rtm-card-text);
            border: 1px solid var(--rtm-card-border);
            box-shadow: var(--rtm-card-shadow);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        /* Theme variables */
        .rtm-widget-card[data-theme="light"] {
            --rtm-card-bg: #ffffff;
            --rtm-card-text: #0f172a;
            --rtm-card-border: #e2e8f0;
            --rtm-card-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.03);
            --rtm-input-bg: #f8fafc;
            --rtm-input-border: #cbd5e1;
            --rtm-btn-bg: #f1f5f9;
            --rtm-btn-text: #334155;
            --rtm-btn-hover: #e2e8f0;
            --rtm-muted: #64748b;
            --rtm-progress-bg: #e2e8f0;
            --rtm-primary: #ea580c;
            --rtm-success: #16a34a;
            --rtm-warning: #d97706;
            --rtm-error: #dc2626;
        }

        .rtm-widget-card[data-theme="dark"] {
            --rtm-card-bg: #0f172a;
            --rtm-card-text: #f8fafc;
            --rtm-card-border: #1e293b;
            --rtm-card-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
            --rtm-input-bg: #1e293b;
            --rtm-input-border: #334155;
            --rtm-btn-bg: #1e293b;
            --rtm-btn-text: #cbd5e1;
            --rtm-btn-hover: #334155;
            --rtm-muted: #94a3b8;
            --rtm-progress-bg: #334155;
            --rtm-primary: #f97316;
            --rtm-success: #22c55e;
            --rtm-warning: #eab308;
            --rtm-error: #ef4444;
        }

        .rtm-widget-header {
            margin-bottom: 20px;
        }
        .rtm-widget-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin: 0;
            color: var(--rtm-card-text);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            letter-spacing: -0.025em;
        }
        .rtm-widget-badge {
            background: var(--rtm-primary);
            color: #ffffff;
            font-size: 0.7rem;
            padding: 2px 8px;
            border-radius: 9999px;
            text-transform: uppercase;
            font-weight: 800;
        }
        .rtm-qr-wrapper {
            background: #ffffff;
            padding: 12px;
            border-radius: 16px;
            display: inline-block;
            margin: 0 auto 20px auto;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease;
        }
        .rtm-qr-wrapper:hover {
            transform: scale(1.02);
        }
        .rtm-qr-placeholder {
            width: 200px;
            height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #94a3b8;
            background: #f8fafc;
            border-radius: 12px;
            border: 2px dashed #cbd5e1;
        }
        .rtm-amount-display {
            font-size: 1.75rem;
            font-weight: 800;
            margin: 0 0 4px 0;
            color: var(--rtm-card-text);
            letter-spacing: -0.03em;
        }
        .rtm-fiat-display {
            font-size: 0.95rem;
            color: var(--rtm-muted);
            margin: 0 0 20px 0;
            font-weight: 500;
        }
        .rtm-input-group {
            display: flex;
            border: 1px solid var(--rtm-input-border);
            border-radius: 12px;
            background: var(--rtm-input-bg);
            overflow: hidden;
            margin-bottom: 20px;
            transition: border-color 0.2s ease;
        }
        .rtm-input-group:focus-within {
            border-color: var(--rtm-primary);
        }
        .rtm-address-input {
            flex: 1;
            border: none;
            background: transparent;
            padding: 12px 16px;
            font-family: monospace;
            font-size: 0.8rem;
            color: var(--rtm-card-text);
            outline: none;
            text-overflow: ellipsis;
        }
        .rtm-copy-btn {
            border: none;
            background: var(--rtm-btn-bg);
            color: var(--rtm-btn-text);
            padding: 0 16px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            border-left: 1px solid var(--rtm-input-border);
        }
        .rtm-copy-btn:hover {
            background: var(--rtm-btn-hover);
        }
        .rtm-progress-container {
            width: 100%;
            height: 6px;
            background: var(--rtm-progress-bg);
            border-radius: 9999px;
            overflow: hidden;
            margin-bottom: 16px;
        }
        .rtm-progress-bar {
            height: 100%;
            background: var(--rtm-primary);
            border-radius: 9999px;
            width: 100%;
            transition: width 1s linear, background-color 0.3s ease;
        }
        .rtm-status-text {
            font-size: 0.85rem;
            color: var(--rtm-muted);
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .rtm-status-pulse {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--rtm-primary);
            animation: rtm-pulse 1.5s infinite ease-in-out;
        }
        .rtm-divider {
            border: 0;
            border-top: 1px solid var(--rtm-card-border);
            margin: 0 0 16px 0;
        }
        .rtm-footer-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .rtm-theme-btn {
            background: transparent;
            border: none;
            color: var(--rtm-muted);
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 8px;
            border-radius: 6px;
            transition: all 0.2s ease;
        }
        .rtm-theme-btn:hover {
            color: var(--rtm-card-text);
            background: var(--rtm-btn-hover);
        }
        .rtm-brand-link {
            font-size: 0.75rem;
            color: var(--rtm-muted);
            text-decoration: none;
            font-weight: 700;
            transition: color 0.2s ease;
        }
        .rtm-brand-link:hover {
            color: var(--rtm-primary);
        }
        
        @keyframes rtm-pulse {
            0% { transform: scale(0.85); opacity: 0.5; }
            50% { transform: scale(1.15); opacity: 1; }
            100% { transform: scale(0.85); opacity: 0.5; }
        }
    `;

  // Helper to inject widget styles once
  function injectStyles() {
    if (document.getElementById(INJECTED_STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = INJECTED_STYLE_ID;
    style.textContent = WIDGET_CSS;
    document.head.appendChild(style);
  }

  const widget = {
    init: function (options = {}) {
      injectStyles();

      const containerId = options.container || "rtm-checkout";
      const container = document.getElementById(containerId);
      if (!container) {
        console.error("RaptoreumPay: Container not found");
        return;
      }

      const invoiceId = container.dataset.invoiceId;
      const apiUrl = container.dataset.apiUrl || "http://localhost:8000";
      const requestedTheme = container.dataset.theme || "system";

      if (!invoiceId || invoiceId === "paste-real-invoice-id-here") {
        container.innerHTML = `
                    <div class="rtm-widget-card" data-theme="dark" style="max-width:400px; padding:40px; border:2px dashed #334155;">
                        <h4 style="font-weight:800; margin:0 0 10px 0; color:#cbd5e1;">RaptoreumPay Sandbox</h4>
                        <p style="font-size:0.9rem; color:#94a3b8; margin:0 0 20px 0; line-height:1.5;">To start simulating a transaction, please create a demo invoice using the generator form.</p>
                        <div class="rtm-qr-placeholder">Pending Invoice ID...</div>
                    </div>
                `;
        return;
      }

      // Determine system theme if 'system'
      let effectiveTheme = requestedTheme;
      if (requestedTheme === "system") {
        effectiveTheme = window.matchMedia("(prefers-color-scheme: dark)")
          .matches
          ? "dark"
          : "light";
      }

      // Load QR code library if not already loaded
      if (!window.QRCode) {
        const script = document.createElement("script");
        script.src =
          "https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js";
        script.onload = () =>
          this.render(container, invoiceId, apiUrl, effectiveTheme);
        document.head.appendChild(script);
      } else {
        this.render(container, invoiceId, apiUrl, effectiveTheme);
      }
    },

    render: function (container, invoiceId, apiUrl, theme) {
      container.innerHTML = `
                <div class="rtm-widget-card" data-theme="${theme}">
                    <div class="rtm-widget-header">
                        <h5 class="rtm-widget-title">
                            Pay with Raptoreum <span class="rtm-widget-badge">RTM</span>
                        </h5>
                    </div>
                    <div class="rtm-qr-wrapper">
                        <div id="rtm-qr-element"></div>
                    </div>
                    <h4 class="rtm-amount-display" id="rtm-amount">-.-------- RTM</h4>
                    <p class="rtm-fiat-display" id="rtm-fiat">Initializing...</p>
                    
                    <div class="rtm-input-group">
                        <input id="rtm-address" type="text" class="rtm-address-input" readonly value="Loading address...">
                        <button id="rtm-copy-btn" class="rtm-copy-btn">Copy</button>
                    </div>
                    
                    <div class="rtm-progress-container">
                        <div id="rtm-progress-bar" class="rtm-progress-bar" style="width: 100%;"></div>
                    </div>
                    
                    <div class="rtm-status-text" id="rtm-status">
                        <span class="rtm-status-pulse" id="rtm-status-pulse"></span>
                        <span id="rtm-status-message">Loading invoice details...</span>
                    </div>
                    
                    <hr class="rtm-divider">
                    
                    <div class="rtm-footer-actions">
                        <button id="rtm-theme-toggle" class="rtm-theme-btn">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
                            Theme
                        </button>
                        <a href="https://raptoreum.com" target="_blank" class="rtm-brand-link">Powered by RaptoreumPay</a>
                    </div>
                </div>
            `;

      const qrElement = container.querySelector("#rtm-qr-element");
      const amountEl = container.querySelector("#rtm-amount");
      const fiatEl = container.querySelector("#rtm-fiat");
      const addressInput = container.querySelector("#rtm-address");
      const copyBtn = container.querySelector("#rtm-copy-btn");
      const statusMessage = container.querySelector("#rtm-status-message");
      const statusPulse = container.querySelector("#rtm-status-pulse");
      const progressBar = container.querySelector("#rtm-progress-bar");
      const themeToggle = container.querySelector("#rtm-theme-toggle");
      const cardElement = container.querySelector(".rtm-widget-card");

      // Fetch invoice details
      fetch(`${apiUrl}/api/payment/${invoiceId}/status`)
        .then((res) => {
          if (!res.ok) throw new Error("Invoice not found");
          return res.json();
        })
        .then((data) => {
          const expires = new Date(data.expires_at);
          const amount = data.amount_requested.toFixed(8);
          const fiat = data.fiat_amount
            ? `≈ $${data.fiat_amount.toFixed(2)} USD`
            : "";

          amountEl.textContent = `${amount} RTM`;
          fiatEl.textContent = fiat;
          addressInput.value = data.address;

          // Clean out old placeholder if any
          qrElement.innerHTML = "";

          // Generate QR Code
          new QRCode(qrElement, {
            text: `raptoreum:${data.address}?amount=${amount}`,
            width: 200,
            height: 200,
            colorDark: "#0f172a", // QR codes should stay dark for contrast / scanner reliability
            colorLight: "#ffffff",
          });

          // Copy action
          copyBtn.onclick = () => {
            navigator.clipboard.writeText(data.address);
            copyBtn.textContent = "Copied!";
            copyBtn.style.color = "var(--rtm-success)";
            setTimeout(() => {
              copyBtn.textContent = "Copy";
              copyBtn.style.color = "var(--rtm-btn-text)";
            }, 2000);
          };

          // Theme toggle action
          themeToggle.onclick = () => {
            const current = cardElement.getAttribute("data-theme");
            const next = current === "dark" ? "light" : "dark";
            cardElement.setAttribute("data-theme", next);
          };

          // Start countdown & status updates
          this.startPollingAndTimer(
            data,
            expires,
            statusMessage,
            statusPulse,
            progressBar,
            cardElement,
            apiUrl,
          );
        })
        .catch((err) => {
          statusMessage.textContent = "Failed to load invoice";
          statusMessage.style.color = "var(--rtm-error)";
          statusPulse.style.background = "var(--rtm-error)";
          statusPulse.style.animation = "none";
          amountEl.textContent = "Error";
          fiatEl.textContent = "Please check backend logs or invoice ID";
          addressInput.value = "N/A";
          console.error(err);
        });
    },

    startPollingAndTimer: function (
      data,
      expires,
      statusMessage,
      statusPulse,
      progressBar,
      cardElement,
      apiUrl,
    ) {
      const totalSeconds = 45 * 60; // 45 minutes duration standard

      // Check remaining duration on init
      const initialRemaining = expires - new Date();
      if (initialRemaining <= 0) {
        statusMessage.textContent = "Invoice expired";
        statusMessage.style.color = "var(--rtm-error)";
        statusPulse.style.background = "var(--rtm-error)";
        statusPulse.style.animation = "none";
        progressBar.style.width = "0%";
        progressBar.style.backgroundColor = "var(--rtm-error)";
        return;
      }

      const timerInterval = setInterval(() => {
        const now = new Date();
        const remaining = expires - now;

        if (remaining <= 0) {
          clearInterval(timerInterval);
          clearInterval(pollInterval);
          statusMessage.textContent = "Invoice expired";
          statusMessage.style.color = "var(--rtm-error)";
          statusPulse.style.background = "var(--rtm-error)";
          statusPulse.style.animation = "none";
          progressBar.style.width = "0%";
          progressBar.style.backgroundColor = "var(--rtm-error)";
          return;
        }

        const secondsLeft = Math.floor(remaining / 1000);
        const percent = (secondsLeft / totalSeconds) * 100;
        progressBar.style.width = `${percent}%`;

        const mins = Math.floor(secondsLeft / 60);
        const secs = secondsLeft % 60;
        statusMessage.textContent = `Awaiting payment... (${mins}:${secs.toString().padStart(2, "0")})`;
      }, 1000);

      // API Poll loop for checking status changes on database
      const pollInterval = setInterval(() => {
        fetch(`${apiUrl}/api/payment/${data.invoice_id}/status`)
          .then((res) => res.json())
          .then((update) => {
            if (update.status === "paid") {
              clearInterval(timerInterval);
              clearInterval(pollInterval);
              statusMessage.textContent = "Payment received! Thank you.";
              statusMessage.style.color = "var(--rtm-success)";
              statusPulse.style.background = "var(--rtm-success)";
              statusPulse.style.animation = "none";
              progressBar.style.width = "100%";
              progressBar.style.backgroundColor = "var(--rtm-success)";
            } else if (update.status === "expired") {
              clearInterval(timerInterval);
              clearInterval(pollInterval);
              statusMessage.textContent = "Invoice expired";
              statusMessage.style.color = "var(--rtm-error)";
              statusPulse.style.background = "var(--rtm-error)";
              statusPulse.style.animation = "none";
              progressBar.style.width = "0%";
              progressBar.style.backgroundColor = "var(--rtm-error)";
            }
          })
          .catch(() => {}); // suppress connection failures silently, try again next tick
      }, 15000); // 15 seconds polling interval
    },
  };

  window.RTMWidget = widget;

  // Auto-initialize widget targets
  document.querySelectorAll('[id="rtm-checkout"]').forEach((el) => {
    widget.init({ container: el.id });
  });
})();
