"""Codegen configuration — the curated tables the auto-builder needs for Tochka.

Everything Tochka-specific lives here; the engine below `engine/` has no spec knowledge.
Two tables carry the weight: `TAG_TO_DOMAIN`, because the portal tags operations in
Russian prose and those tags are the only grouping the spec offers, and `ENTITY_BINDINGS`,
which turns a path token into a bound method on the model that owns it.
"""

from __future__ import annotations

from typing import Final

#: Base URL per product, verbatim from each spec's `servers` block. They are NOT the same
#: host: cyclops lives on api.tochka.com entirely, pay-gateway adds a `pay/` prefix. A
#: client with one base URL sends 73 of 167 methods to the wrong place.
PRODUCT_BASE_URLS: Final[dict[str, tuple[str, str | None]]] = {
    # product: (production, sandbox/test or None)
    "tochka-api": ("https://enter.tochka.com/uapi/", "https://enter.tochka.com/sandbox/v2/"),
    "info": ("https://enter.tochka.com/uapi/", "https://enter.tochka.com/sandbox/v2/"),
    "express-credit": ("https://enter.tochka.com/uapi/", "https://enter.tochka.com/sandbox/v2/"),
    "medusa": ("https://enter.tochka.com/uapi/", "https://stage-uapi.tochka.com/uapi/"),
    "pay-gateway": ("https://enter.tochka.com/uapi/pay/", None),
    "cyclops": ("https://api.tochka.com/api/v1/cyclops", "https://pre.tochka.com/api/v1/cyclops"),
}

PRODUCTION_BASE_URL: Final = PRODUCT_BASE_URLS["tochka-api"][0]
SANDBOX_BASE_URL: Final = PRODUCT_BASE_URLS["tochka-api"][1]
#: Domain-level docs link. The portal has no per-tag page, so this points at the catalogue;
#: per-operation links live on each operation as `x-portal-url` (set by `scraper.py`).
DOCS_URL_TEMPLATE: Final = "https://developers.tochka.com/docs"

#: Logical host key every generated method targets (matches ``BaseMethod.__host__`` default).
DEFAULT_HOST: Final = "uapi"

#: Header params handled by the transport/auth layer — dropped from generated method fields.
SKIP_HEADER_PARAMS: Final[frozenset[str]] = frozenset(
    {"authorization", "content-type", "accept", "x-request-id", "sign", "sign-system", "sign-thumbprint"},
)

#: Write verbs whose retries must carry an ``Idempotency-Key``.
IDEMPOTENT_VERBS: Final[frozenset[str]] = frozenset({"PUT", "PATCH", "DELETE"})

#: Portal tag (verbatim, per product) → module basename under `methods/`, `models/`, `enums/`.
#: The portal writes tags as Russian prose, so this table is the ONLY reliable grouping —
#: transliterating them yields unusable module names. An unmapped tag is a hard error
#: (see `fetch.domain_for_tag`), never a silent `misc.py` dump.
TAG_TO_DOMAIN: Final[dict[tuple[str, str], str]] = {
    # tochka-api — the main Open Banking surface
    ("tochka-api", "Работа с балансами счетов"): "balances",
    ("tochka-api", "Работа со счетами"): "accounts",
    ("tochka-api", "Работа с клиентами"): "customers",
    ("tochka-api", "Работа с платежами"): "payments",
    ("tochka-api", "Работа с платёжными ссылками"): "payment_links",
    ("tochka-api", "Работа с выставлением счетов"): "invoices",
    ("tochka-api", "Работа с выписками"): "statements",
    ("tochka-api", "Работа с закрывающими документами"): "closing_documents",
    ("tochka-api", "Работа с подписками"): "subscriptions",
    ("tochka-api", "Работа с вебхуками"): "webhooks",
    ("tochka-api", "Работа с разрешениями"): "permissions",
    ("tochka-api", "Сервис СБП: Работа с QR-кодами"): "sbp_qr_codes",
    ("tochka-api", "Сервис СБП: Работа с кассовыми QR-кодами"): "sbp_cashbox_qr_codes",
    ("tochka-api", "Сервис СБП: Работа с ЮЛ"): "sbp_legal_entities",
    ("tochka-api", "Сервис СБП: Работа с ТСП"): "sbp_merchants",
    ("tochka-api", "Сервис СБП: Работа с возвратами"): "sbp_refunds",
    ("tochka-api", "Сервис СБП: работа с B2B QR-кодами"): "sbp_b2b_qr_codes",
    # cyclops — nominal accounts / escrow
    ("cyclops", "Бенефициары"): "beneficiaries",
    ("cyclops", "Сделки"): "deals",
    ("cyclops", "Платежи"): "nominal_payments",
    ("cyclops", "Виртуальные счета"): "virtual_accounts",
    ("cyclops", "Документы"): "nominal_documents",
    ("cyclops", "Загрузка документов"): "nominal_document_uploads",
    ("cyclops", "СБП"): "nominal_sbp",
    ("cyclops", "Доступность сервиса"): "nominal_health",
    # pay-gateway — internet acquiring
    ("pay-gateway", "Кассовые ссылки СБП"): "acquiring_cashbox_links",
    ("pay-gateway", "Функциональные ссылки СБП"): "acquiring_functional_links",
    ("pay-gateway", "Вебхуки"): "acquiring_webhooks",
    ("pay-gateway", "Возвраты"): "acquiring_refunds",
    ("pay-gateway", "Подтверждение"): "acquiring_confirmation",
    ("pay-gateway", "Платёж через форму мерчанта"): "acquiring_merchant_form",
    ("pay-gateway", "[WIP] Платёж через форму банка"): "acquiring_bank_form",
    ("pay-gateway", "Платёжные токены"): "acquiring_payment_tokens",
    ("pay-gateway", "Завершение аутентификации"): "acquiring_authentication",
    # medusa — marketplace payouts
    ("medusa", "Заказы"): "marketplace_orders",
    ("medusa", "Получатели"): "marketplace_recipients",
    # express-credit
    ("express-credit", "Работа с Экспресс кредитами"): "express_credits",
    # info — a single customer lookup published as its own product
    ("info", "Работа с клиентами"): "customer_info",
}

#: Path-parameter token (snake_cased) → (entity model class, self attribute).
#: Drives bound-method generation: `await payment.get()` fills `{paymentId}` from
#: `payment.payment_id`. `customer_code` is account context, resolved from the client.
ENTITY_BINDINGS: Final[dict[str, tuple[str, str]]] = {
    "account_id": ("Account", "account_id"),
    "payment_id": ("Payment", "payment_id"),
    "qrc_id": ("QrCode", "qrc_id"),
    "legal_id": ("LegalEntity", "legal_id"),
    "merchant_id": ("Merchant", "merchant_id"),
    "webhook_id": ("Webhook", "webhook_id"),
    "deal_id": ("Deal", "deal_id"),
    "beneficiary_id": ("Beneficiary", "beneficiary_id"),
    "virtual_account": ("VirtualAccount", "virtual_account"),
    "document_id": ("Document", "document_id"),
    "request_id": ("PaymentLink", "request_id"),
}

#: Path tokens filled from the client's own context, never from a model field.
ACCOUNT_CONTEXT_PARAMS: Final[frozenset[str]] = frozenset({"customer_code", "customerCode"})

#: Products the generator walks, in emission order.
PRODUCTS: Final[tuple[str, ...]] = (
    "tochka-api",
    "cyclops",
    "pay-gateway",
    "medusa",
    "express-credit",
    "info",
)


def module_for_slug(slug: str) -> str:
    """Return the ``methods/<name>.py`` basename for a domain slug."""

    return slug.replace("-", "_")
