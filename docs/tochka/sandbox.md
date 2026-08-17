# Песочница

```python
from tochka import Client, Environment

async with Client(token="working_token", environment=Environment.SANDBOX) as client:
    balances = await client.get_balances_list()
```

Токен `working_token` опубликован банком в разделе «Песочница» — договор для него не нужен.

## Что доступно

| Продукт | Тестовый сервер |
|---|---|
| `tochka-api`, `info`, `express-credit` | `https://enter.tochka.com/sandbox/v2/` |
| `cyclops` | `https://pre.tochka.com/api/v1/cyclops` |
| `medusa` | `https://stage-uapi.tochka.com/uapi/` |
| `pay-gateway` | **нет** |

Обращение к `pay-gateway` из песочницы даёт `ConfigurationError` — SDK не подставит боевой
адрес молча. Нужен стенд от банка — задайте его явно:

```python
config = Config(
    token="...",
    environment=Environment.SANDBOX,
    product_base_urls={Product.PAY_GATEWAY: "https://выданный-стенд/uapi/pay/"},
)
```

## Чего песочница не проверяет

- **Разрешения.** Боевой токен ограничен списком `permissions`; песочница отвечает на то,
  что в проде вернёт 403.
- **Вебхуки.** Нужен публичный HTTPS‑адрес на порту 443; локальный сервер банк не увидит.
  Проверять приёмник имеет смысл своим ключом (`StaticKeyProvider`) — так это делают тесты
  SDK, `tests/test_webhooks.py`.
- **Деньги и лимиты.** Комиссии, лимиты выплат и антифрод в песочнице не воспроизводятся.

## Что стоит прогнать перед продом

1. `get_customers_list()` → `get_accounts_list()` — токен живой, доступ есть.
2. `get_balances_list()` — разбор конверта `{Data, Links, Meta}`.
3. `init_statement(...)` → `get_statement(...)` — асинхронная выписка.
4. Ваш ключевой сценарий (платёжная ссылка либо QR СБП) до статуса оплаты.
