# Устройство SDK

Граница одна: **методы, модели, enum'ы и фасады генерируются из спецификации банка,
остальное написано руками**. Файл с шапкой `AUTO-GENERATED` править бесполезно — следующая
регенерация его перезапишет (в CI это отдельная проверка).

```
tochka/
  client.py          Client — единственный, кто ходит в сеть
  config.py          Config: токены и базовые URL по продуктам
  exceptions.py      иерархия ошибок
  pagination.py      MethodPaginator + два стиля пагинации
  types.py           Product, Environment, доменные примитивы
  methods/_base.py   BaseMethod[T] — эндпоинт как класс
  models/_base.py    TochkaObject — базовая DTO
  models/common.py   TZDatetime, общее тело ошибки
  facade/_base.py    контракт, на который опирается генерируемый код
  transport/         сессия, retry, rate limit, разбор ошибок
  webhooks/          приём и проверка вебхуков
  methods|models|enums|facade/*   ← ГЕНЕРИРУЕТСЯ (154 файла)
```

## Поток одного вызова

```
client.get_balance_info(account_id=…)          фасад (генерируется)
  └─ GetBalanceInfo(account_id=…)              метод-класс: валидация полей
      └─ Client.execute()
          ├─ base_url_for(method.__product__)   выбор ХОСТА по продукту
          ├─ token_for(product)                 выбор токена
          ├─ RateLimiter.acquire()
          ├─ HttpxSession.request()
          ├─ parse_error() при не-2xx           → типизированная ошибка
          └─ model.model_validate() + as_()     → модель, привязанная к клиенту
```

## Почему так

**Метод — класс, а не функция.** Экземпляр это уже провалидированный запрос: поля описаны
типами, путь и продукт объявлены `ClassVar`. Клиенту не нужно знать, что такое эндпоинт, а
объект вызова можно передать, сохранить и выполнить позже.

**Продукт живёт на методе.** У Точки шесть продуктов на трёх хостах; `__product__` на классе
означает, что маршрут нельзя забыть указать — он приезжает вместе с методом.

**Фасады собраны статически.** `facade/_generated.py` — обычное наследование, а не
`type(...)`: динамическая база невидима для mypy и IDE, и все 167 методов теряют
автодополнение.

**Модель знает свой клиент.** `as_()` привязывает его рекурсивно, поэтому у ответа работают
методы вроде `await payment.get_payment_status()` без повторной передачи идентификаторов.

**Транспорт за ABC.** `BaseSession` позволяет подменить его в тестах без патчинга —
`tests/conftest.py` так и делает.

## Что где чинить

| Симптом | Куда смотреть |
|---|---|
| метод уходит не на тот хост | `config.PRODUCT_BASE_URLS`, `__product__` метода |
| ответ не разбирается | модель домена; при ошибке летит `ResponseValidationError` |
| нужен новый метод после обновления API | `python -m dev.codegen scrape && generate` |
| странное имя метода / коллизия | `dev/codegen/engine/collisions.py` |
| нет пагинации там, где она есть | `dev/codegen/engine/build.py`, `PAGINATION_STYLES` |

Полное описание генератора — [`dev/codegen/_MODULE.md`](../../dev/codegen/_MODULE.md).
