# Установка

## Одной командой

```bash
pip install tochka-sdk
```

С приёмом вебхуков (тянет `fastapi` и `uvicorn`):

```bash
pip install "tochka-sdk[webhooks]"
```

Проверка, что всё встало:

```bash
python -c "import tochka; print(tochka.__version__)"
```

Требуется **Python 3.11+**. Зависимости ядра: `httpx`, `pydantic` v2, `pyjwt[crypto]`.

## Другие менеджеры пакетов

```bash
uv add tochka-sdk
poetry add tochka-sdk
pdm add tochka-sdk
```

## Из репозитория

Пока пакет не опубликован в PyPI либо нужна неотрелизованная правка:

```bash
pip install "git+https://github.com/zlexdev/tochka-sdk.git@main"
```

## Что нужно, кроме пакета

| Нужно | Где взять |
|---|---|
| Токен Open Banking | личный кабинет Точки → приложение → JWT-ключ |
| `customer_code` | `await client.get_customers_list()` — их может быть несколько |
| Разрешения (`permissions`) | выдаются ключу при создании; проверить — `get_all_consents_list()` |

Токен нужен не всякому вызову одинаковый: `cyclops`, `medusa` и `pay-gateway` — отдельные
продукты банка со своими хостами и подключением. Подробности — [авторизация](../tochka/auth.md).

Первый вызов без договора делается в песочнице:

```python
from tochka import Client, Environment

async with Client(token="working_token", environment=Environment.SANDBOX) as client:
    print(await client.get_balances_list())
```

## Установка для разработки

```bash
git clone https://github.com/zlexdev/tochka-sdk.git
cd tochka-sdk
python -m venv .venv && .venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,webhooks]"
```

Проверка, что окружение рабочее — тот же гейт, что гоняет CI:

```bash
ruff check tochka dev scripts tests
mypy tochka
pytest tests -q
python scripts/lint_spec_bindings.py --strict
```

Последняя команда — не формальность: она сверяет 167 операций спецификации со 167 методами
SDK и падает, если хоть одна осталась без метода.

## Обновление surface под новую версию API

Методы не пишутся руками — они генерируются из спецификаций банка:

```bash
python scripts/download_tochka_specs.py     # портал -> docs/tochka/api/
python -m dev.codegen scrape                # -> dev/generated/openapi/
python -m dev.codegen generate              # -> tochka/{methods,models,enums,facade}/
python -m dev.codegen check                 # ruff + mypy
python scripts/generate_method_reference.py # docs/sdk/methods.md
```

Файл с шапкой `AUTO-GENERATED` править бесполезно — CI отдельной джобой проверяет, что
повторная генерация ничего не меняет, и падает, если кто-то правил такой файл руками.

## Частые проблемы

**`ConfigurationError: у продукта 'pay-gateway' нет тестового сервера`** — банк не публикует
песочницу для эквайринга. Работайте с ним в `Environment.PRODUCTION` либо задайте свой стенд
через `product_base_urls`.

**`403 Forbidden by consent`** — ключу не выдано нужное разрешение либо метод адресован не тому
клиенту. Посмотрите `get_all_consents_list()` и переберите `get_customers_list()`: у одного
токена бывает несколько `customer_code`, и услуга подключена только к одному из них.

**`424 Retailer not found`** — доступ есть, но у клиента нет торговой точки: интернет-эквайринг
не подключён. Это настройка в кабинете банка, не в коде.
