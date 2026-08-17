# dev/codegen

Спека Точки → `tochka/{methods,models,enums,facade}/`. Движок спеко-агностичен: вся
специфика Точки живёт в `config.py` и `fetch.py`, ниже `engine/` о банке не знает ничего.

## Конвейер

```
scripts/download_tochka_specs.py   портал → docs/tochka/api/<product>.json
scraper.py                         → dev/generated/openapi/tochka_<product>.json (OpenAPI 3)
fetch.py                           домен = (продукт, тег) → срез спеки
parser.py                          OpenAPI → IR (Domain / Operation / Param / Prop)
engine/build.py                    IR → MethodSpec / ModelSpec / GeneratedDomain
engine/emit_*.py                   → исходники
engine/dedup.py, collisions.py     кросс-доменные проходы (общие модели, уникальность имён)
engine/generate.py                 запись + `facade/_generated.py`
```

Команды: `scrape` · `generate [--slug X] [--dry-run]` · `check`.

## Что правится при изменениях API

| Что случилось | Куда идти |
|---|---|
| банк добавил раздел (новый тег) | `config.TAG_TO_DOMAIN` — незамапленный тег это ошибка, а не `misc.py` |
| появился новый продукт | `config.PRODUCTS` + `scraper.PRODUCT_TITLES` |
| нужен bound-метод на новой сущности | `config.ENTITY_BINDINGS` |
| новый стиль пагинации | `build.PAGINATION_STYLES` + класс в `tochka/pagination.py` |
| заголовок, который держит транспорт | `config.SKIP_HEADER_PARAMS` |

## Ловушки движка

**Схемы у Точки всегда inline.** `op.response_ref` — None везде. Каждая проверка на него
молча выключает фичу; так уже случилось трижды (пагинация, сущности, bound-методы).
Используйте `op.response_inline` или `response_models`, собранный в `build_domain`.

**Сущность лежит внутри `Data`.** `_entity_model()` разворачивает конверт
`{Data, Links, Meta}` перед поиском поля-идентификатора.

**`operationId` — FastAPI-стиль.** Хвост `<путь>_<метод>` срезается в
`scraper.normalise_operation_id`, иначе класс называется `GetBalanceInfoOpenBankingV10...`.

**Докстринги переносит `render.wrap`, а не `ruff format`** — форматтер прозу внутри
докстринга не трогает, а описания банка бывают по 300 символов. Ширина считается по самому
широкому префиксу (первая строка + `"""`, продолжения + висячий отступ).

**Дефолт enum-поля — член enum, не строка.** `_enum_default()` в `types.py`; иначе mypy
ругается на код, который автор не может исправить руками.

## Проверка

`python -m dev.codegen check` (ruff + mypy) и `scripts/lint_spec_bindings.py --strict`
(167 операций спеки ↔ 167 методов SDK). CI дополнительно требует, чтобы перегенерация была
no-op: правка сгенерированного файла руками иначе доживёт до первой чужой регенерации.
