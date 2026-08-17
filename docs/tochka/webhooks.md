# Вебхуки

**Ловушка: тело вебхука — это не JSON.** Точка присылает `POST` с
`Content-Type: text/plain`, в теле — «голая» строка JWT, подписанная RS256. `await
request.json()` на нём падает; читать нужно сырое тело.

## Что приходит

Пять событий:

| `webhookType` | Когда |
|---|---|
| `incomingPayment` | зачисление на счёт |
| `outgoingPayment` | списание со счёта |
| `incomingSbpPayment` | оплата по СБП |
| `incomingSbpB2BPayment` | оплата по B2B QR‑коду СБП |
| `acquiringInternetPayment` | оплата по платёжной ссылке |

Полезные поля лежат в payload JWT: `customerCode`, `paymentId`, `purpose`, суммы, а у
платёжных событий — блоки `SidePayer` и `SideRecipient`.

## Проверка подписи — обязательна

Публичный ключ банка: `https://enter.tochka.com/doc/openapi/static/keys/public` (JWK).
В примерах банка ключ вписан в код — **так делать не надо**: при ротации всё встанет. SDK
скачивает ключ сам, кэширует и перезапрашивает один раз при несовпадении подписи.

```python
from fastapi import FastAPI, Request, Response
from tochka.webhooks import WebhookReceiver, WebhookType

app = FastAPI()
receiver = WebhookReceiver()


@receiver.on(WebhookType.INCOMING_PAYMENT)
async def credited(event) -> None:
    ...


@app.post("/tochka/webhook")
async def hook(request: Request) -> Response:
    try:
        await receiver.handle(await request.body())    # именно body()
    except Exception:
        return Response(status_code=500)
    return Response(status_code=200)
```

## Ретраи: 200 значит «доставлено навсегда»

Если ответ не 200, банк повторит доставку **30 раз с интервалом 10 секунд**. Отсюда два
следствия, и оба неочевидны:

- **Отвечать 200 на необработанном событии нельзя** — повтора не будет, платёж потерян.
  Обработка должна упасть с 5xx, а не проглотиться.
- **Обработчик обязан быть идемпотентным** — одно и то же событие придёт несколько раз при
  любой вашей заминке. Ключ дедупликации — `paymentId` (или `operationId` у эквайринга).

## Подключение

```python
from tochka.enums.webhooks import CreateWebhookWebhooksList as Event

await client.create_webhook(
    client_id=APP_CLIENT_ID,
    url="https://shop.example/tochka/webhook",
    webhooks_list=[Event.INCOMINGPAYMENT, Event.ACQUIRINGINTERNETPAYMENT],
)
```

Требования банка, из-за которых создание вебхука падает чаще всего:

- только **HTTPS и только порт 443**;
- при создании и изменении банк отправляет тестовое событие на **каждый** тип из списка — не
  ответите 200, вебхук не создастся;
- нужно разрешение `ManageWebhookData`.

Управление: `get_webhooks(client_id)`, `edit_webhook(...)`, `delete_webhook(...)`,
`send_webhook(...)` — последний присылает тестовое событие вручную.

## Если вебхук не пришёл

Банк прямо советует не полагаться на них как на единственный канал. Дублирующая проверка:

- оплата по платёжной ссылке → `get_payment_operation_info(operation_id)`;
- оплата по QR → `get_qr_codes_payment_status(qrc_ids)`;
- зачисление по реквизитам → выписка: `init_statement(...)` затем `get_statement(...)`.

Вебхуки приходят **только по успешным** операциям — отказ по платежу событием не приедет.
