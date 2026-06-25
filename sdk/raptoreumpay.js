const crypto = require("crypto");

class RaptoreumPayClient {
  constructor(apiKey, baseUrl = "http://localhost:8000") {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async _request(method, path, body = null) {
    const url = `${this.baseUrl}${path}?api_key=${encodeURIComponent(this.apiKey)}`;
    const options = {
      method,
      headers: {
        "Accept": "application/json",
      }
    };

    if (body !== null) {
      options.body = JSON.stringify(body);
      options.headers["Content-Type"] = "application/json";
    }

    try {
      const res = await fetch(url, options);
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch (e) {
        data = text;
      }

      if (!res.ok) {
        const detail = data && data.detail ? (typeof data.detail === "object" ? JSON.stringify(data.detail) : data.detail) : text;
        throw new Error(`RaptoreumPay API Error (${res.status}): ${detail}`);
      }

      return data;
    } catch (err) {
      throw new Error(`RaptoreumPay Request Connection Error: ${err.message}`);
    }
  }

  createInvoice({ amountRtm, amountFiat, fiatCurrency, orderId, webhookUrl } = {}) {
    const params = {};
    if (amountRtm !== undefined) params.amount_rtm = amountRtm;
    if (amountFiat !== undefined) params.amount_fiat = amountFiat;
    if (fiatCurrency !== undefined) params.fiat_currency = fiatCurrency;
    if (orderId !== undefined) params.order_id = orderId;
    if (webhookUrl !== undefined) params.webhook_url = webhookUrl;

    return this._request("POST", "/api/payment/create", params);
  }

  getInvoiceStatus(invoiceId) {
    return this._request("GET", `/api/payment/${invoiceId}/status`);
  }

  static verifyWebhookSignature(payloadBuffer, signature, timestamp, apiKey, maxAgeSeconds = 300) {
    try {
      // Prevent replay attacks
      const now = Math.floor(Date.now() / 1000);
      const sigTime = parseInt(timestamp, 10);
      if (isNaN(sigTime) || Math.abs(now - sigTime) > maxAgeSeconds) {
        return false;
      }

      // Convert payload to buffer if string
      const payload = typeof payloadBuffer === "string" ? Buffer.from(payloadBuffer, "utf-8") : payloadBuffer;

      // Construct signed payload buffer
      const prefix = Buffer.from(`${timestamp}.`, "utf-8");
      const signedPayload = Buffer.concat([prefix, payload]);

      // Compute HMAC-SHA256
      const computed = crypto
        .createHmac("sha256", apiKey)
        .update(signedPayload)
        .digest("hex");

      // Timing-attack resistant verification
      const computedBuffer = Buffer.from(computed, "hex");
      const sigBuffer = Buffer.from(signature, "hex");

      if (computedBuffer.length !== sigBuffer.length) {
        return false;
      }

      return crypto.timingSafeEqual(computedBuffer, sigBuffer);
    } catch (e) {
      return false;
    }
  }
}

module.exports = { RaptoreumPayClient };
