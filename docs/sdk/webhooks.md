# Приём вебхуков

Как устроены вебхуки у банка — в [docs/tochka/webhooks.md](../tochka/webhooks.md). Здесь —
только API SDK.

```python
from tochka.webhooks import WebhookReceiver, WebhookType

receiver = WebhookReceiver()


@receiver.on(WebhookType.INCOMING_PAYMENT)
async def credited(event) -> None:
    ...

event = await receiver.handle(raw_body)     # проверит подпись и вызовет обработчики
```

`handle()` принимает `bytes` или `str` — сырое тело запроса, не JSON.

## Фреймворк не важен

`WebhookReceiver` ничего не знает про FastAPI, aiohttp и Django: он принимает тело и
возвращает событие. Обёртку пишете вы — три строки в любом фреймворке.

```python
@app.post("/tochka/webhook")
async def hook(request: Request) -> Response:
    try:
        await receiver.handle(await request.body())
    except Exception:
        return Response(status_code=500)   # 200 = «доставлено», повтора не будет
    return Response(status_code=200)
```

## Только проверка, без обработчиков

```python
event = await receiver.verify(raw_body)
```

## Ключ

По умолчанию скачивается с `enter.tochka.com/doc/openapi/static/keys/public` и кэшируется;
при несовпадении подписи запрашивается ещё раз (ротация ключа иначе положила бы приём
целиком). Свой ключ — для тестов и закрытых контуров:

```python
from tochka.webhooks import StaticKeyProvider

receiver = WebhookReceiver(keys=StaticKeyProvider(jwk_dict))
```

## Типы событий

`PaymentEvent` (`incomingPayment`, `outgoingPayment`) · `SbpPaymentEvent`
(`incomingSbpPayment`, `incomingSbpB2BPayment`) · `AcquiringEvent`
(`acquiringInternetPayment`).

**Незнакомый тип не роняет приёмник** — приезжает `UnknownEvent` с сохранённым payload
(`event.raw()`). Новое событие банка не должно останавливать обработку остальных.

## Ошибки

`WebhookVerificationError` — тело пустое, не JWT, или подпись не сошлась даже со свежим
ключом. Это единственный класс, который стоит ловить отдельно: всё остальное — ошибки ваших
обработчиков, и их должно быть видно.
