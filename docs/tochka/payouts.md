# Выплаты: три механизма, и они не взаимозаменяемы

Первое решение — **чьи деньги вы платите**. От него зависит продукт, договор и налоги, а не
только код.

| Чьи деньги | Механизм | Продукт | Типичный случай |
|---|---|---|---|
| ваши | маркетплейс‑выплаты | `medusa` | реферальные вознаграждения, выплаты исполнителям |
| клиентов, вы их держите | номинальный счёт | `cyclops` | эскроу, балансы пользователей, сделки |
| ваши, разово | платёжное поручение | `tochka-api` | оплата контрагенту‑юрлицу |

## 1. Medusa — выплаты физлицам, в том числе по СБП

Механика: деньги приходят вам, вы описываете «заказ» — кому и сколько, — банк делит сумму на
выплату получателю и вашу комиссию и пробивает чек.

| Шаг | Метод SDK |
|---|---|
| завести получателя | `create_recipient(ext_id, name, sbp=...)` |
| выплата по СБП | `add_sbp_recipient_payout_method(recipient_ext_id, sbp_payout_method=...)` |
| выплата на карту | `add_card_recipient_payout_method(...)` |
| банки СБП | `list_recipient_sbp_banks()` |
| создать выплату | `create_order_v3(incoming_payment, services=[...], ext_id, receipt=...)` |
| подтвердить услугу | `make_order_services_decision(...)` |
| статус, отчёт | `get_order_v3(order_ext_id)`, `get_order_report(...)` |

Ключевое поле — `Services[]`: каждая позиция несёт получателя, `price` (сумма ему) и
`commission` (ваша доля). Делить платёж руками не нужно; `Receipt` закрывает 54‑ФЗ.

### Реферальная программа целиком

```python
from tochka.models.marketplace_recipients import AddSbpRecipientPayoutMethodDataSbpPayoutMethod
from tochka.models.marketplace_orders import CreateOrderV3DataServices

banks = await client.list_recipient_sbp_banks()          # bankId выбирает сам реферал

recipient = await client.create_recipient(ext_id=f"ref-{user_id}", name=full_name)

await client.add_sbp_recipient_payout_method(
    recipient_ext_id=recipient.data.ext_id,
    sbp_payout_method=AddSbpRecipientPayoutMethodDataSbpPayoutMethod(
        bank_id=chosen_bank_id,
        payout_method_ext_id=f"sbp-{user_id}",
    ),
)

await client.create_order_v3(
    ext_id=f"payout-{period}-{user_id}",     # ключ идемпотентности, см. ниже
    incoming_payment=...,
    services=[CreateOrderV3DataServices(
        recipient=...,
        price="500.00",
        commission="0.00",
        ext_id=f"ref-{period}-{user_id}",
    )],
)
```

**`ext_id` — единственная защита от двойной выплаты.** Считайте его из (период, пользователь),
никогда не из случайного значения: при ретрае после таймаута случайный ключ создаст второй
заказ и вторую выплату.

## 2. Cyclops — номинальный счёт

Берётся, когда деньги пользователей обязаны лежать отдельно от ваших. Бенефициары
(`create_beneficiary_v3` — ИП, самозанятый, физлицо), у каждого виртуальный счёт, между ними
сделки.

| Задача | Метод |
|---|---|
| завести получателя денег | `create_beneficiary_v3(...)` |
| счёт бенефициара | `create_virtual_account_v2(...)` |
| сделка (кто → кому) | `create_deal_v2(...)` |
| исполнить сделку | `execute_deal_v2(deal_id, recipients_execute=[...])` |
| вывести деньги | `refund_virtual_account_v2(...)` |
| налоги за физлицо | `payment_of_taxes_v2(...)`, счёт типа `for_ndfl` |
| пополнение по СБП | `generate_sbp_qrcode_v2(...)` |
| движение по счёту | `list_virtual_transaction_v2(...)` |

**Cyclops говорит по JSON‑RPC, а не REST**: у каждого метода тело `{id, jsonrpc, method,
params}`, и полезные поля лежат в `params`. Фасад SDK это разворачивает — вы передаёте поля
плоско, а объект `params` собирается за вас.

## 3. Платёжное поручение

`create_payment_for_sign(...)` + `get_payment_status(request_id)`. Требует подписи
(`CreatePaymentForSign`), предназначено для расчётов с юрлицами, а не для потока выплат
физлицам.

## Что решается не кодом

- **Подключение продукта.** `medusa` и `cyclops` не открываются токеном Open Banking, у них
  свои хосты и своё подключение. Это упрётся раньше, чем любая строчка SDK.
- **Налоги за получателя.** Выплата физлицу — НДФЛ либо статус самозанятого. Medusa умеет
  чек, cyclops — отдельный счёт под НДФЛ; какую схему выбрать, решаете вы.
- **Проверка получателя.** Bank ID для СБП выбирает сам получатель; ошибка в нём — деньги
  ушли не туда, и вернуть их API не даст.
