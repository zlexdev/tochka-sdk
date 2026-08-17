# Карта проекта для ИИ-агента

Читать это вместо вычитывания исходников. Здесь — границы, инварианты и места, где ломается.

## Что это

Асинхронный SDK для Open API Точка Банка. **167 методов сгенерированы** из спецификаций
банка; ядро (клиент, транспорт, пагинация, вебхуки) написано руками.

```
tochka/
  client.py            Client — единственный, кто ходит в сеть
  config.py            Config: PRODUCT_BASE_URLS, token_for(), base_url_for()
  exceptions.py        иерархия ошибок; ветвиться по .code, не по тексту
  pagination.py        MethodPaginator, PageMethod, OffsetMethod
  types.py             Product, Environment, доменные примитивы
  methods/_base.py     BaseMethod[T]: __http_method__, __endpoint__, __product__
  models/_base.py      TochkaObject: alias-поля, extra=allow, as_()
  models/common.py     TZDatetime, TochkaErrorBody — генератор импортирует ПО ИМЕНИ
  facade/_base.py      контракт для генерируемых миксинов: execute(), paginate()
  facade/_generated.py ГЕНЕРИРУЕТСЯ: статическая база из 38 фасадов
  transport/           session (httpx за ABC), retry, rate limit, разбор ошибок
  webhooks/            приём JWT-вебхуков: keys, events, receiver
  methods|models|enums|facade/*   ГЕНЕРИРУЕТСЯ — 154 файла

dev/codegen/           OpenAPI → surface; config.py и fetch.py знают про Точку, engine/ — нет
scripts/               скачивание спек, гейт покрытия, генератор справочника
docs/sdk/              документация по коду; docs/tochka/ — по самому банку
```

## Инварианты, которые нельзя нарушать

**Файл с шапкой `AUTO-GENERATED` не редактируется.** CI проверяет, что повторная генерация
не меняет дерево. Правка нужна — правьте генератор (`dev/codegen/`), не результат.

**Продукт определяет ХОСТ.** `cyclops` — `api.tochka.com`, `pay-gateway` — `uapi/pay/`,
остальные — `enter.tochka.com/uapi/`. Хост берётся из `method.__product__`, не из конфига
«вообще». Проверка живёт в `tests/test_products.py`.

**Схемы у банка всегда inline.** `$ref` не встречается нигде. Любая новая проверка на
`op.response_ref` молча отключит фичу — так уже было трижды (пагинация, bound-методы,
определение сущностей). Смотрите `op.response_inline`.

**Поля спеки затеняют атрибуты.** В ответах есть `client`, `payload`, `url`, `type`. Поэтому
служебные методы `BaseMethod` подчёркнуты (`_url_path`, `_request_payload`, `_returning`), а у
модели вместо свойства `client` — метод `bound_client()`. Не добавляйте публичный атрибут с
именем, которое может прийти с провода.

**Имена ClassVar в генераторе и базе обязаны совпадать.** Генератор пишет
`__idempotent_mutation__`, `__binary_response__`, `__product__`. Рассогласование тихое: код
работает, флаг просто всегда ложный.

## Как что-то поменять

| Задача | Куда |
|---|---|
| банк добавил раздел | `dev/codegen/config.py` → `TAG_TO_DOMAIN` (незамапленный тег = ошибка, не `misc.py`) |
| новый продукт | `config.PRODUCTS` + `PRODUCT_BASE_URLS` (в обоих config.py — codegen и `tochka/`) |
| bound-метод на сущности | `config.ENTITY_BINDINGS` |
| новый стиль пагинации | `engine/build.py` → `PAGINATION_STYLES` + класс в `tochka/pagination.py` |
| поведение клиента | `tochka/client.py` — руками, генератор его не трогает |

## Проверки

```bash
ruff check tochka dev scripts tests
mypy tochka                                  # strict, 177 файлов
pytest tests -q                              # 34 теста, сеть не нужна
python scripts/lint_spec_bindings.py --strict  # 167 операций ↔ 167 методов
```

Тесты работают через `FakeSession` (`tests/conftest.py`) — токен и сеть не требуются.

## Дальше

- [Справочник всех методов](../sdk/methods.md) — генерируется из кода
- [Устройство SDK](../sdk/architecture.md) — поток одного вызова
- [Ловушки Точка API](../tochka/traps.md) — то, чего нет в документации банка
- [Генератор](../../dev/codegen/_MODULE.md) — как обновлять surface
