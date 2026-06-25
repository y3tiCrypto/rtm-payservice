<?php

class RaptoreumPayClient {
    private $apiKey;
    private $baseUrl;

    public function __construct(string $apiKey, string $baseUrl = "http://localhost:8000") {
        $this->apiKey = $apiKey;
        $this->baseUrl = rtrim($baseUrl, "/");
    }

    private function request(string $method, string $path, array $data = null) {
        $url = $this->baseUrl . $path;
        if ($method === "POST" || $method === "GET") {
            $url .= "?api_key=" . urlencode($this->apiKey);
        }

        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);

        $headers = [];
        if ($data !== null) {
            $jsonData = json_encode($data);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $jsonData);
            $headers[] = "Content-Type: application/json";
            $headers[] = "Content-Length: " . strlen($jsonData);
        }
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        
        if (curl_errno($ch)) {
            $error = curl_error($ch);
            curl_close($ch);
            throw new Exception("RaptoreumPay Request Connection Error: " . $error);
        }
        curl_close($ch);

        $decoded = json_decode($response, true);
        if ($httpCode >= 400) {
            $detail = isset($decoded["detail"]) ? (is_array($decoded["detail"]) ? json_encode($decoded["detail"]) : $decoded["detail"]) : $response;
            throw new Exception("RaptoreumPay API Error ($httpCode): " . $detail);
        }

        return $decoded;
    }

    public function createInvoice(
        float $amountRtm = null,
        float $amountFiat = null,
        string $fiatCurrency = null,
        string $orderId = null,
        string $webhookUrl = null
    ) {
        $params = [];
        if ($amountRtm !== null) $params["amount_rtm"] = $amountRtm;
        if ($amountFiat !== null) $params["amount_fiat"] = $amountFiat;
        if ($fiatCurrency !== null) $params["fiat_currency"] = $fiatCurrency;
        if ($orderId !== null) $params["order_id"] = $orderId;
        if ($webhookUrl !== null) $params["webhook_url"] = $webhookUrl;

        return $this->request("POST", "/api/payment/create", $params);
    }

    public function getInvoiceStatus(string $invoiceId) {
        // Fetch invoice status using the endpoint format
        return $this->request("GET", "/api/payment/{$invoiceId}/status");
    }

    public static function verifyWebhookSignature(
        string $payloadBytes,
        string $signature,
        string $timestamp,
        string $apiKey,
        int $maxAgeSeconds = 300
    ): bool {
        // Prevent replay attacks by checking signature age
        if (abs(time() - (int)$timestamp) > $maxAgeSeconds) {
            return false;
        }

        // Construct signed payload string
        $signedPayload = $timestamp . "." . $payloadBytes;

        // Compute Expected HMAC-SHA256 signature
        $computed = hash_hmac("sha256", $signedPayload, $apiKey);

        // Timing-attack resistant verification comparison
        return hash_equals($computed, $signature);
    }
}
