from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Optional
import httpx


@dataclass
class ProviderConfig:
    provider: str
    api_id: Optional[str]
    api_key: Optional[str]
    project_id: Optional[str]
    webhook_secret: Optional[str]
    success_url: Optional[str]
    fail_url: Optional[str]
    app_base_url: Optional[str]


class PaymentProvider:
    def __init__(self, cfg: ProviderConfig) -> None:
        self.cfg = cfg

    async def create_invoice(self, match_id: int, amount_rub: int, description: str) -> str:
        if self.cfg.provider == "mock":
            return f"{(self.cfg.app_base_url or '').rstrip('/')}/mockpay/{match_id}?amount={amount_rub}"
        # Пример для реального провайдера (заглушка)
        # endpoint = "https://provider.example.com/api/v1/invoices"
        # payload = {
        #     "project_id": self.cfg.project_id,
        #     "amount": amount_rub,
        #     "currency": "RUB",
        #     "order_id": str(match_id),
        #     "description": description,
        #     "success_url": self.cfg.success_url,
        #     "fail_url": self.cfg.fail_url,
        # }
        # headers = {"X-API-ID": self.cfg.api_id, "X-API-KEY": self.cfg.api_key}
        # async with httpx.AsyncClient(timeout=20.0) as client:
        #     resp = await client.post(endpoint, json=payload, headers=headers)
        #     resp.raise_for_status()
        #     data = resp.json()
        #     return data["invoice_url"]
        raise RuntimeError("Real provider not configured")

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        if self.cfg.provider == "mock":
            return True
        if not self.cfg.webhook_secret:
            return False
        mac = hmac.new(self.cfg.webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(mac, signature)


def load_provider() -> PaymentProvider:
    cfg = ProviderConfig(
        provider=os.getenv("PAYMENT_PROVIDER", "mock"),
        api_id=os.getenv("PAYMENT_API_ID"),
        api_key=os.getenv("PAYMENT_API_KEY"),
        project_id=os.getenv("PAYMENT_PROJECT_ID"),
        webhook_secret=os.getenv("PAYMENT_WEBHOOK_SECRET"),
        success_url=os.getenv("PAYMENT_SUCCESS_URL"),
        fail_url=os.getenv("PAYMENT_FAIL_URL"),
        app_base_url=os.getenv("APP_BASE_URL"),
    )
    return PaymentProvider(cfg)


