// RaptoreumPay Widget - Bootstrap 5 responsive payment embed
// Usage: <div id="rtm-checkout" data-invoice-id="..." data-api-url="..." data-theme="dark|light"></div>

(function () {
    if (window.RTMWidget) return; // prevent multiple loads

    const widget = {
        init: function (options = {}) {
            const containerId = options.container || 'rtm-checkout';
            const container = document.getElementById(containerId);
            if (!container) {
                console.error('RaptoreumPay: Container not found');
                return;
            }

            const invoiceId = container.dataset.invoiceId;
            const apiUrl = container.dataset.apiUrl || 'http://localhost:8000';
            const theme = container.dataset.theme || 'system'; // 'light', 'dark', 'system'

            if (!invoiceId) {
                container.innerHTML = '<div class="alert alert-danger">Missing data-invoice-id</div>';
                return;
            }

            // Apply Bootstrap theme
            let effectiveTheme = theme;
            if (theme === 'system') {
                effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            }
            container.setAttribute('data-bs-theme', effectiveTheme);

            // Load QR code library if not already loaded
            if (!window.QRCode) {
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js';
                script.onload = () => this.render(container, invoiceId, apiUrl, effectiveTheme);
                document.head.appendChild(script);
            } else {
                this.render(container, invoiceId, apiUrl, effectiveTheme);
            }
        },

        render: function (container, invoiceId, apiUrl, theme) {
            container.innerHTML = `
                <div class="card shadow-sm h-100">
                    <div class="card-body text-center">
                        <h5 class="card-title mb-4">Pay with Raptoreum (RTM)</h5>
                        <div id="qr-container" class="mb-3 mx-auto" style="max-width:220px;"></div>
                        <h4 id="amount" class="fw-bold mb-2"></h4>
                        <p id="fiat" class="text-muted mb-3"></p>
                        <div class="input-group mb-3">
                            <input id="address" type="text" class="form-control" readonly>
                            <button id="copy-btn" class="btn btn-outline-secondary">Copy</button>
                        </div>
                        <div class="progress mb-3" style="height:10px;">
                            <div id="timer-progress" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width:100%"></div>
                        </div>
                        <small id="status" class="text-muted">Waiting for payment...</small>
                        <hr>
                        <button id="theme-toggle" class="btn btn-outline-secondary btn-sm">Toggle Theme</button>
                    </div>
                </div>
            `;

            const qrContainer = container.querySelector('#qr-container');
            const amountEl = container.querySelector('#amount');
            const fiatEl = container.querySelector('#fiat');
            const addressInput = container.querySelector('#address');
            const copyBtn = container.querySelector('#copy-btn');
            const statusEl = container.querySelector('#status');
            const progress = container.querySelector('#timer-progress');
            const themeToggle = container.querySelector('#theme-toggle');

            // Fetch invoice data
            fetch(`${apiUrl}/api/payment/${invoiceId}/status`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'error') throw new Error(data.detail || 'Unknown error');

                    const expires = new Date(data.expires_at);
                    const amount = data.amount_requested.toFixed(8);
                    const fiat = data.fiat_amount ? `≈ $${data.fiat_amount.toFixed(2)} USD` : '';

                    amountEl.textContent = `${amount} RTM`;
                    fiatEl.textContent = fiat;
                    addressInput.value = data.address;

                    // QR Code
                    new QRCode(qrContainer, {
                        text: `raptoreum:${data.address}?amount=${amount}`,
                        width: 220,
                        height: 220,
                        colorDark: theme === 'dark' ? "#ffffff" : "#000000",
                        colorLight: theme === 'dark' ? "#1a1a1a" : "#ffffff"
                    });

                    // Copy button
                    copyBtn.onclick = () => {
                        navigator.clipboard.writeText(data.address);
                        copyBtn.textContent = 'Copied!';
                        setTimeout(() => copyBtn.textContent = 'Copy', 2000);
                    };

                    // Theme toggle
                    themeToggle.onclick = () => {
                        const current = container.getAttribute('data-bs-theme');
                        const next = current === 'dark' ? 'light' : 'dark';
                        container.setAttribute('data-bs-theme', next);
                    };

                    // Start countdown & polling
                    this.startPollingAndTimer(data, expires, statusEl, progress, container);
                })
                .catch(err => {
                    statusEl.textContent = 'Error loading payment info';
                    statusEl.className = 'text-danger';
                    console.error(err);
                });
        },

        startPollingAndTimer: function (data, expires, statusEl, progress, container) {
            const startTime = new Date();
            const totalSeconds = 45 * 60; // 45 minutes

            const timerInterval = setInterval(() => {
                const now = new Date();
                const remaining = expires - now;

                if (remaining <= 0) {
                    clearInterval(timerInterval);
                    clearInterval(pollInterval);
                    statusEl.textContent = 'Invoice expired';
                    statusEl.className = 'text-warning';
                    progress.style.width = '0%';
                    return;
                }

                const secondsLeft = Math.floor(remaining / 1000);
                const percent = (secondsLeft / totalSeconds) * 100;
                progress.style.width = `${percent}%`;

                statusEl.textContent = `Waiting for payment... (${Math.floor(secondsLeft / 60)}:${(secondsLeft % 60).toString().padStart(2, '0')})`;
            }, 1000);

            const pollInterval = setInterval(() => {
                fetch(`${container.dataset.apiUrl}/api/payment/${data.invoice_id}/status`)
                    .then(res => res.json())
                    .then(update => {
                        if (update.status === 'paid') {
                            clearInterval(timerInterval);
                            clearInterval(pollInterval);
                            statusEl.textContent = 'Payment received! Thank you!';
                            statusEl.className = 'text-success fw-bold';
                            progress.className = 'progress-bar bg-success';
                            progress.style.width = '100%';
                        } else if (update.status === 'expired') {
                            clearInterval(timerInterval);
                            clearInterval(pollInterval);
                            statusEl.textContent = 'Invoice expired';
                            statusEl.className = 'text-warning';
                        }
                    })
                    .catch(() => {}); // silent fail
            }, 15000); // poll every 15 seconds
        }
    };

    window.RTMWidget = widget;

    // Auto-init if elements exist
    document.querySelectorAll('[id="rtm-checkout"]').forEach(el => {
        widget.init({ container: el.id });
    });
})();