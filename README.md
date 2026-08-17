<p align="center">
  <img src="https://github.com/zlexdev.png" alt="tochka-sdk" width="96" height="96" style="border-radius:24px">
</p>

<h1 align="center">tochka-sdk</h1>

<p align="center">
  <strong>Асинхронный SDK для Open API Точка Банка: 167 методов, сгенерированных из спецификаций банка</strong>
</p>

<p align="center">
  <a href="https://github.com/zlexdev/tochka-sdk/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/zlexdev/tochka-sdk/ci.yml?branch=main&style=for-the-badge&label=CI" alt="CI"></a>
  <a href="https://pypi.org/project/tochka-sdk/"><img src="https://img.shields.io/pypi/v/tochka-sdk?style=for-the-badge&color=blue" alt="PyPI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-blue?style=for-the-badge" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="MIT"></a>
</p>

**tochka-sdk** — типизированный асинхронный клиент Open API Точка Банка: счета, платежи, СБП,
выписки, эквайринг, номинальные счета и выплаты. Своей спецификации банк не публикует, поэтому
она собирается с портала разработчика, а поверхность SDK генерируется из неё — покрытие
сверяется командой, а не на глаз: **167 операций спецификации, 167 методов**.

[Документация](docs/README.md) · [Установка](docs/sdk/installation.md) · [Все методы](docs/sdk/methods.md) · [Про сам банк](docs/tochka/README.md) · [Для ИИ-агентов](docs/for_ai/index.md) · [Issues](https://github.com/zlexdev/tochka-sdk/issues)

## Установка

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

Приём вебхуков — `pip install "tochka-sdk[webhooks]"`. Первый вызов без договора делается в
песочнице: `Client(token="working_token", environment=Environment.SANDBOX)`.

Подробнее — [гайд по установке](docs/sdk/installation.md).

## Что покрыто

| Продукт | Методов | Что внутри |
|---|---|---|
| `tochka-api` | 71 | счета, балансы, платежи, выписки, СБП, платёжные ссылки, вебхуки |
| `cyclops` | 47 | номинальные счета: бенефициары, сделки, виртуальные счета |
| `pay-gateway` | 26 | интернет-эквайринг: формы оплаты, возвраты, токены карт |
| `medusa` | 19 | маркетплейс: заказы и выплаты получателям по СБП и на карты |
| `express-credit` | 3 | экспресс-кредиты |
| `info` | 1 | справка о клиенте |

Шесть продуктов живут на трёх разных хостах, и SDK выбирает нужный сам — по продукту метода,
а не по одному базовому URL на весь клиент.

## Примеры

### Приём оплаты по QR СБП с опросом статуса

Когда принимающего URL нет: скрипт, десктоп, касса. Запрос-ответ, без входящих соединений.

```python
from tochka import Client
from tochka.enums.sbp_qr_codes import RegisterQrCodeDataQrcType as QrcType

async with Client(token=TOKEN) as client:
    qr = await client.register_qr_code(
        account_id="40802810000000000000/044525104",   # ваш счёт
        merchant_id="MA0000000000",                    # ТСП из get_merchants_list()
        payment_purpose="Заказ № 1024",
        qrc_type=QrcType.V_02,      # динамический: сумма зашита в QR
        amount=10_000,              # копейки
        currency="RUB",
        ttl=60,
    )
    print(qr.data.payload)          # https://qr.nspk.ru/... — это и есть ссылка на оплату

    status = await client.get_qr_codes_payment_status(qrc_ids=qr.data.qrc_id)
```

### Событийный приём: вебхуки

Продакшн-путь. Банк присылает событие сам, опрашивать ничего не нужно.

```python
from fastapi import FastAPI, Request, Response
from tochka.webhooks import WebhookReceiver, WebhookType

app = FastAPI()
receiver = WebhookReceiver()


@receiver.on(WebhookType.INCOMING_PAYMENT)
async def credited(event) -> None:
    await orders.mark_paid(event.payment_id, amount=event.payer.amount)


@app.post("/tochka/webhook")
async def hook(request: Request) -> Response:
    try:
        await receiver.handle(await request.body())   # body(), не json()
    except Exception:
        return Response(status_code=500)              # 200 = «доставлено», повтора не будет
    return Response(status_code=200)
```

Тело вебхука — не JSON, а строка JWT, подписанная RS256. Подпись проверяется публичным ключом
банка, который SDK скачивает и обновляет сам.

### Обход больших выборок и аналитика

Пагинация спрятана за курсором: запрос не уходит, пока курсор не начали обходить.

```python
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from tochka.models.statements import InitStatementDataStatement

started = await client.init_statement(
    statement=InitStatementDataStatement(
        account_id=account_id,
        start_date_time=date.today() - timedelta(days=30),
        end_date_time=date.today(),
    ),
)
statement = await client.get_statement(
    account_id=account_id,
    statement_id=started.data.statement.statement_id,
)

incoming: dict[str, Decimal] = defaultdict(Decimal)
for block in statement.data.statement:
    for transaction in block.transaction or []:
        if transaction.credit_debit_indicator == "Credit":
            payer = transaction.debtor_party.name if transaction.debtor_party else "не указан"
            incoming[payer] += Decimal(str(transaction.amount.amount))

# страницы и элементы — один и тот же метод, без *_paginated двойников
async for page in client.get_subscription_list(customer_code=code):
    ...
async for item in client.get_subscription_list(customer_code=code).items():
    ...
```

### Несколько продуктов банка одним клиентом

Выплаты (`medusa`) и номинальные счета (`cyclops`) — отдельные продукты со своими хостами и
подключением. Каждому можно дать свой токен; хост подставляется по методу.

```python
from tochka import Client, Config
from tochka.types import Product

config = Config(
    token=OPEN_BANKING_TOKEN,
    product_tokens={Product.MEDUSA: MEDUSA_TOKEN},
    customer_code="300123456",
)

async with Client(config=config) as client:
    recipient = await client.create_recipient(ext_id=f"ref-{user_id}", name=full_name)
    await client.add_sbp_recipient_payout_method(
        recipient_ext_id=recipient.data.ext_id,
        sbp_payout_method=payout_method,
    )
    await client.create_order_v3(ext_id=f"payout-{period}-{user_id}", ...)  # выплата по СБП
```

## Ошибки и повторы

```python
from tochka import ApiError, NotFoundError, PermissionDeniedError, RateLimitError

try:
    await client.get_balance_info(account_id=account_id)
except PermissionDeniedError as error:
    error.code       # AccessDenied — из Errors[0].errorCode, а не HTTP-статус строкой
    error.error_id   # идентификатор для поддержки банка
```

Повторы делаются сами: 429 и 5xx на идемпотентных вызовах, экспоненциальная пауза с джиттером,
`Retry-After` банка имеет приоритет. Ответ, не совпавший с моделью, поднимает
`ResponseValidationError`, а не деградирует в `dict`: изменение формата видно на месте вызова.

## Разработка

```bash
git clone https://github.com/zlexdev/tochka-sdk.git && cd tochka-sdk
pip install -e ".[dev,webhooks]"
pytest tests -q                                 # 34 теста, сеть не нужна
python scripts/lint_spec_bindings.py --strict   # 167 операций ↔ 167 методов
```

Методы не пишутся руками — они генерируются: `python -m dev.codegen generate`. Файл с шапкой
`AUTO-GENERATED` править бесполезно, CI проверяет, что повторная генерация ничего не меняет.
Детали — [устройство SDK](docs/sdk/architecture.md) и [генератор](dev/codegen/_MODULE.md).

## Community

Баги и предложения — [issues](https://github.com/zlexdev/tochka-sdk/issues/new/choose).
Pull request'ы приветствуются: перед отправкой прогоните гейт из раздела «Разработка» —
тот же набор гоняет CI.

<a href="https://github.com/zlexdev"><img src="https://github.com/zlexdev.png" width="48" height="48" style="border-radius:50%" alt="zlexdev"></a>

## License

[MIT](LICENSE) © 2026 tochka-sdk contributors
