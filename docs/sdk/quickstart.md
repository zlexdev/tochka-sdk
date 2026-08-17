# Быстрый старт

```bash
pip install tochka-sdk
```

```python
import asyncio
from tochka import Client


async def main() -> None:
    async with Client(token="...", customer_code="300123456") as client:
        balances = await client.get_balances_list()
        for balance in balances.data.balance:
            print(balance.account_id, balance.amount.amount, balance.amount.currency)


asyncio.run(main())
```

`customer_code` задаётся один раз — все методы с сегментом `{customerCode}` подставят его сами.

## Клиент

```python
Client(
    token="...",                       # либо config=Config(...)
    customer_code="300123456",
    environment=Environment.SANDBOX,   # по умолчанию PRODUCTION
    timeout=30.0,
    max_retries=3,
    requests_per_second=10.0,
)
```

Клиент — асинхронный контекст: `async with` закроет соединения. Своя сессия
(`session=...`) не закрывается — закрывает тот, кто её создал.

Разные токены на разные продукты (`cyclops`, `medusa`, `pay-gateway` подключаются
отдельно) — см. [авторизацию](../tochka/auth.md).

## Три способа вызвать метод

```python
# 1. Метод на клиенте — обычный путь
balance = await client.get_balance_info(account_id="40817810802000000008/044525104")

# 2. Класс метода — когда объект вызова нужно передать или сохранить
from tochka.methods.balances import GetBalanceInfo
balance = await client.execute(GetBalanceInfo(account_id="..."))

# 3. Метод на модели — идентификаторы берутся из неё самой
status = await payment.get_payment_status()
```

## Ответы

Модели типизированы и повторяют конверт банка: `result.data`, `result.links`, `result.meta`.
Поля переименованы в snake_case, оригинал доступен через `.raw()`.

Неизвестные поля **сохраняются**: банк добавляет их без смены версии, и отбросить их значило
бы сделать обновление SDK единственным способом увидеть новые данные.

## Ошибки

```python
from tochka import ApiError, AuthenticationError, NotFoundError, PermissionDeniedError, RateLimitError

try:
    await client.get_balance_info(account_id="...")
except PermissionDeniedError as error:
    ...            # 403: не выдано разрешение
except NotFoundError:
    ...            # 404
except RateLimitError as error:
    error.retry_after
except ApiError as error:
    error.status, error.code, error.message, error.error_id
```

Повторы делаются сами: 429 и 5xx на идемпотентных вызовах, экспоненциальная пауза с
джиттером, `Retry-After` банка имеет приоритет. Неидемпотентные записи получают
`Idempotency-Key` и повторяются только если помечены безопасными к повтору.

Дальше: [пагинация](pagination.md) · [вебхуки](webhooks.md) ·
[справочник методов](methods.md) · [архитектура](architecture.md)
