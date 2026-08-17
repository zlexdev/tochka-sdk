"""Client configuration — one frozen object, built from typed values, never strings."""

from __future__ import annotations

from dataclasses import dataclass, field

from .exceptions import ConfigurationError
from .types import Environment, Product

#: Base URL per product, taken from each spec's own `servers` block. These are NOT one
#: host with different prefixes: cyclops lives on api.tochka.com entirely, and pay-gateway
#: adds `pay/`. Sending every product to one base URL silently misroutes 73 of 167 methods.
PRODUCT_BASE_URLS: dict[Product, tuple[str, str | None]] = {
    # product: (production, sandbox/test — None when the bank publishes no test server)
    Product.TOCHKA_API: ("https://enter.tochka.com/uapi/", "https://enter.tochka.com/sandbox/v2/"),
    Product.MEDUSA: ("https://enter.tochka.com/uapi/", "https://stage-uapi.tochka.com/uapi/"),
    Product.PAY_GATEWAY: ("https://enter.tochka.com/uapi/pay/", None),
    Product.CYCLOPS: ("https://api.tochka.com/api/v1/cyclops", "https://pre.tochka.com/api/v1/cyclops"),
    Product.EXPRESS_CREDIT: ("https://enter.tochka.com/uapi/", "https://enter.tochka.com/sandbox/v2/"),
    Product.INFO: ("https://enter.tochka.com/uapi/", "https://enter.tochka.com/sandbox/v2/"),
}

PRODUCTION_BASE_URL = PRODUCT_BASE_URLS[Product.TOCHKA_API][0]
SANDBOX_BASE_URL = PRODUCT_BASE_URLS[Product.TOCHKA_API][1]

#: Sandbox tokens are published by the bank in its own docs — the SDK ships one so the
#: first call works without an application, exactly as the portal's "Песочница" page says.
SANDBOX_TOKEN = "working_token"


@dataclass(frozen=True, slots=True)
class Config:
    """Everything the transport needs to make one call.

    `customer_code` is the account context: every endpoint with a `{customerCode}` segment
    fills it from here, so it is passed once instead of on every call.
    """

    token: str
    environment: Environment = Environment.PRODUCTION
    customer_code: str | None = None
    #: Per-product overrides. Cyclops and pay-gateway are separate bank products with their
    #: own onboarding — their credentials are usually NOT the Open Banking token, so each
    #: can carry its own. A product absent here falls back to `token`.
    product_tokens: dict[Product, str] = field(default_factory=dict)
    #: Per-product base-URL overrides — for a dedicated stand or a host the bank moved.
    product_base_urls: dict[Product, str] = field(default_factory=dict)
    timeout: float = 30.0
    max_retries: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 8.0
    requests_per_second: float = 10.0
    user_agent: str = "tochka-sdk/0.1.0"
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.token:
            raise ConfigurationError("token пуст — без него не пройдёт ни один вызов")
        if self.timeout <= 0:
            raise ConfigurationError(f"timeout должен быть положительным, получен {self.timeout}")
        if self.max_retries < 0:
            raise ConfigurationError(f"max_retries не может быть отрицательным, получен {self.max_retries}")
        if self.requests_per_second <= 0:
            raise ConfigurationError(
                f"requests_per_second должен быть положительным, получен {self.requests_per_second}",
            )

    @property
    def base_url(self) -> str:
        """Base URL of the main Open Banking surface — see `base_url_for` for the rest."""

        return self.base_url_for(Product.TOCHKA_API)

    def base_url_for(self, product: Product) -> str:
        """Base URL for one product, honouring an explicit override.

        Raises when the bank publishes no test server for that product (pay-gateway):
        falling back to production from a sandbox client would move real money.
        """

        if product in self.product_base_urls:
            return self.product_base_urls[product]

        production, sandbox = PRODUCT_BASE_URLS[product]
        if self.environment is not Environment.SANDBOX:
            return production
        if sandbox is None:
            raise ConfigurationError(
                f"у продукта {product.value!r} нет тестового сервера — задайте product_base_urls"
                f"[{product!r}] явно либо работайте с ним в Environment.PRODUCTION",
            )
        return sandbox

    def token_for(self, product: Product) -> str:
        """Token for one product; falls back to the main token when none is set."""

        return self.product_tokens.get(product, self.token)

    @classmethod
    def sandbox(cls, token: str = SANDBOX_TOKEN, **kwargs: object) -> Config:
        """Config pointed at the bank's sandbox."""

        return cls(token=token, environment=Environment.SANDBOX, **kwargs)  # type: ignore[arg-type]
