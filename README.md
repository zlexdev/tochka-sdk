# tochka-sdk

[![ci](https://github.com/zlexdev/tochka-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/zlexdev/tochka-sdk/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](https://pypi.org/project/tochka-sdk/)

Асинхронный SDK для Open API Точка Банка. 167 методов, сгенерированных из спецификации банка, с типами, моделями ответов и приёмом вебхуков.

```python
from tochka import Client

async with Client(token="...", customer_code="300123456") as client:
    balances = await client.get_balances_list()
    for balance in balances.data.balance:
        print(balance.account_id, balance.amount.amount, balance.amount.currency)
```

## Установка

```bash
pip install tochka-sdk
```

Приём вебхуков — `pip install "tochka-sdk[webhooks]"`.

## Что покрыто

| Продукт | Методов | О чём |
|---|---|---|
| `tochka-api` | 71 | счета, балансы, платежи, выписки, СБП, платёжные ссылки, вебхуки |
| `cyclops` | 47 | номинальные счета: бенефициары, сделки, виртуальные счета |
| `pay-gateway` | 26 | интернет-эквайринг: ссылки, возвраты, токены |
| `medusa` | 19 | маркетплейс: заказы и получатели выплат |
| `express-credit` | 3 | экспресс-кредиты |
| `info` | 1 | справка по клиенту |

Покрытие проверяется командой, а не на глаз:

```bash
python scripts/lint_spec_bindings.py --strict
# Операций в спеке: 167, {'bound': 167, 'unbound': 0, 'duplicate': 0, 'orphan': 0}
```

## Песочница

```python
from tochka import Client, Environment

async with Client(token="working_token", environment=Environment.SANDBOX) as client:
    ...
```

## Полный сценарий: выставить счёт и дождаться оплаты

Оплата ловится **двумя способами**, и они взаимозаменяемы: вебхуком (мгновенно, банк
приходит сам) или опросом метода (когда принимающего URL нет — крон, скрипт, десктоп).
Ниже оба, вокруг одной и той же операции.

### Шаг 1. Создать платёжную ссылку

```python
from tochka import Client
from tochka.enums.payment_links import CreatePaymentOperationDataPaymentMode

async with Client(token=TOKEN, customer_code="300123456") as client:
    operation = await client.create_payment_operation(
        amount=1990.0,
        customer_code="300123456",
        purpose="Оплата заказа № 1024",
        payment_mode=[CreatePaymentOperationDataPaymentMode.SBP,
                      CreatePaymentOperationDataPaymentMode.CARD],
        redirect_url="https://shop.example/thanks",
        fail_redirect_url="https://shop.example/failed",
        ttl=60,                      # ссылка живёт час
    )

    link = operation.data.payment_link       # это отдаём покупателю
    operation_id = operation.data.operation_id   # это сохраняем у себя в заказе
```

`operation_id` — ключ, по которому платёж потом опознаётся и в вебхуке, и при опросе.
Сохраните его рядом с заказом до того, как показать ссылку.

### Шаг 2а. Принять оплату вебхуком

```python
from fastapi import FastAPI, Request, Response
from tochka.webhooks import WebhookReceiver, WebhookType

app = FastAPI()
receiver = WebhookReceiver()


@receiver.on(WebhookType.ACQUIRING_INTERNET_PAYMENT)
async def paid(event) -> None:
    order = await orders.find_by_operation(event.operation_id)
    if order is None or order.paid:
        return                       # повтор доставки — не двойное зачисление
    await orders.mark_paid(order.id, amount=event.amount, payment_id=event.payment_id)


@app.post("/tochka/webhook")
async def hook(request: Request) -> Response:
    try:
        await receiver.handle(await request.body())
    except Exception:
        # 200 говорит банку «доставлено» — отдавать его на необработанном событии нельзя,
        # иначе платёж потерян: банк не пришлёт его снова.
        return Response(status_code=500)
    return Response(status_code=200)
```

Подписка на события делается один раз, из того же SDK:

```python
from tochka.enums.webhooks import CreateWebhookWebhooksList as Event

await client.create_webhook(
    client_id=APP_CLIENT_ID,
    url="https://shop.example/tochka/webhook",
    webhooks_list=[Event.INCOMINGPAYMENT, Event.ACQUIRINGINTERNETPAYMENT],
)
```

Банк проверит доступность URL тестовой отправкой на каждое событие — если в ответ придёт
не 200, вебхук не создастся. Только HTTPS, только порт 443.

### Шаг 2б. Принять оплату опросом — если вебхук некуда принимать

```python
import asyncio
from tochka.enums.payment_links import GetPaymentOperationInfoResponseDataOperationStatus as Status

FINAL = {Status.EXPIRED, Status.REFUNDED, Status.REFUNDED_PARTIALLY}


async def wait_for_payment(client, operation_id: str, *, timeout: float = 3600) -> bool:
    """Опрашивать статус, пока не оплатят или не истечёт срок ссылки."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        info = await client.get_payment_operation_info(operation_id=operation_id)
        status = info.data.operation[0].status      # операция приходит списком
        if status is Status.APPROVED:
            return True
        if status in FINAL:
            return False
        await asyncio.sleep(15)
    return False
```

Оба пути дают одно и то же и дополняют друг друга: вебхук как основной канал, опрос — как
подстраховка для заказов, по которым уведомление не пришло. Сам банк советует ровно это.

### Шаг 3. Вернуть деньги

```python
refund = await client.refund_payment_operation(
    operation_id=operation_id,
    amount=1990.0,
)
```

## Приём по QR-коду СБП

```python
from tochka.enums.sbp_qr_codes import RegisterQrCodeDataQrcType

qr = await client.register_qr_code(
    account_id="40802810500000000001/044525104",
    merchant_id=MERCHANT_ID,
    payment_purpose="Оплата заказа № 1024",
    qrc_type=RegisterQrCodeDataQrcType.V_02,   # 01 — статический, 02 — динамический
    amount=199000,                # копейки
    currency="RUB",
    ttl=60,
)

status = await client.get_qr_codes_payment_status(qrc_ids=qr.data.qrc_id)
```

Событие оплаты приедет тем же приёмником, тип — `WebhookType.INCOMING_SBP_PAYMENT`.

## Аналитика по выписке

Выписка формируется асинхронно: сначала заказ, потом чтение готового документа.

```python
from datetime import date, timedelta
from tochka.models.statements import InitStatementDataStatement

account_id = "40802810500000000001/044525104"

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
```

### Оборот по контрагентам за месяц

```python
from collections import defaultdict
from decimal import Decimal

incoming: dict[str, Decimal] = defaultdict(Decimal)

for block in statement.data.statement:
    for transaction in block.transaction or []:
        if transaction.credit_debit_indicator != "Credit":
            continue
        payer = transaction.debtor_party.name if transaction.debtor_party else "не указан"
        incoming[payer] += Decimal(str(transaction.amount.amount))

for payer, total in sorted(incoming.items(), key=lambda pair: pair[1], reverse=True)[:10]:
    print(f"{total:>14,.2f} ₽  {payer}")
```

### Расходы по назначению платежа

```python
outgoing: dict[str, Decimal] = defaultdict(Decimal)

for block in statement.data.statement:
    for transaction in block.transaction or []:
        if transaction.credit_debit_indicator == "Credit":
            continue
        purpose = (transaction.description or "").split(".")[0][:60]
        outgoing[purpose] += Decimal(str(transaction.amount.amount))
```

Суммы складывайте только `Decimal` — `float` из JSON теряет копейки на больших оборотах.

### Сводный остаток по всем счетам

```python
balances = await client.get_balances_list()

total = sum(
    Decimal(str(balance.amount.amount))
    for balance in balances.data.balance
    if balance.credit_debit_indicator == "Credit"
)
```

### Сверка: что банк считает оплаченным, а мы — нет

```python
paid_by_bank = {
    transaction.payment_id
    for block in statement.data.statement
    for transaction in block.transaction or []
    if transaction.credit_debit_indicator == "Credit"
}

missing = paid_by_bank - await orders.known_payment_ids()
```

## Регулярные списания (подписки)

```python
subscription = await client.create_subscription(
    amount=590.0,
    customer_code="300123456",
    purpose="Подписка «Про», месяц",
    save_card=True,
    recurring=True,
)

# следующий месяц — списание без участия клиента
await client.charge_subscription(operation_id=subscription.data.operation_id, amount=590.0)
```

## Пагинация

Пагинируемый метод возвращает курсор — запрос не уходит, пока его не дождались или не начали обходить:

```python
first_page = await client.get_subscriptions(customer_code="300123456")

async for page in client.get_subscriptions(customer_code="300123456"):
    ...

async for item in client.get_subscriptions(customer_code="300123456").items():
    ...
```

Точка пагинирует двумя способами — `page`/`perPage` и `limit`/`offset`; оба скрыты за одним курсором.

## Методы на моделях

Объект, пришедший в ответе, знает свой клиент, поэтому следующий вызов не требует повторять идентификаторы:

```python
status = await payment.get_payment_status()   # request_id подставится из самого объекта
```

## Ошибки

```python
from tochka import ApiError, NotFoundError, PermissionDeniedError, RateLimitError

try:
    await client.get_balance_info(account_id="...")
except PermissionDeniedError as error:
    print(error.code)      # AccessDenied — из Errors[0].errorCode
    print(error.error_id)  # идентификатор для обращения в поддержку
```

Повторы выполняются сами: 429 и 5xx на идемпотентных вызовах, с экспоненциальной паузой и учётом `Retry-After`.

## Вебхуки

Точка присылает `POST` с телом `text/plain`, в котором лежит **строка JWT**, подписанная RS256. Подпись проверяется публичным ключом банка, который скачивается и обновляется автоматически.

```python
from fastapi import FastAPI, Request, Response
from tochka.webhooks import WebhookReceiver, WebhookType

app = FastAPI()
receiver = WebhookReceiver()


@receiver.on(WebhookType.INCOMING_PAYMENT)
async def on_payment(event):
    print(event.payment_id, event.payer.name, event.purpose)


@app.post("/tochka")
async def hook(request: Request) -> Response:
    await receiver.handle(await request.body())   # именно body(), не json()
    return Response(status_code=200)
```

Ответ, отличный от 200, заставит банк повторить доставку 30 раз с интервалом 10 секунд. Подключить вебхук можно только по HTTPS на порт 443.

Пять событий: `incomingPayment`, `outgoingPayment`, `incomingSbpPayment`, `incomingSbpB2BPayment`, `acquiringInternetPayment`.

## Обновление под новую версию API

Спецификации банка нет в открытом виде — портал отдаёт её по частям, поэтому она скачивается и собирается:

```bash
python scripts/download_tochka_specs.py    # портал -> docs/tochka/api/*.json
python -m dev.codegen scrape               # -> dev/generated/openapi/*.json
python -m dev.codegen generate             # -> tochka/{methods,models,enums,facade}/
python -m dev.codegen check                # ruff + mypy
python scripts/lint_spec_bindings.py --strict
```

Файлы с шапкой `AUTO-GENERATED` правит генератор; руками написаны только клиент, транспорт, авторизация, пагинация и вебхуки.

## Документация

[`docs/`](docs/README.md) — два набора:

- **по SDK**: [быстрый старт](docs/sdk/quickstart.md) · [все 167 методов](docs/sdk/methods.md) ·
  [пагинация](docs/sdk/pagination.md) · [вебхуки](docs/sdk/webhooks.md) ·
  [устройство](docs/sdk/architecture.md)
- **по Точка Банку**: [как устроен API](docs/tochka/README.md) ·
  [авторизация](docs/tochka/auth.md) · [выплаты](docs/tochka/payouts.md) ·
  [вебхуки](docs/tochka/webhooks.md) · [песочница](docs/tochka/sandbox.md) ·
  [ловушки](docs/tochka/traps.md)

## Лицензия

MIT.
