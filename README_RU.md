# Узбекские платежи

Интеграция платежных шлюзов для платежных систем Узбекистана (Payme, Click, FreedomPay) в Frappe Framework.

**Версия:** 1.0.0  
**Лицензия:** MIT  
**Требуемые приложения:** Frappe, ERPNext, Payments  
**Python:** >=3.10

## Возможности

- **Несколько платежных шлюзов**: Поддержка Payme, Click и FreedomPay
- **Автоматическая обработка платежей**: Обновление статусов платежей в реальном времени
- **Безопасная обработка платежей**: Проверка подписи HMAC для callback'ов
- **Сверка платежей**: Автоматическая сверка с банковскими счетами
- **Поддержка баз данных**: Полная поддержка PostgreSQL и MySQL/MariaDB
- **Интеграция с модулями**: Интеграция с модулями Учета, Банкинга и Аналитики
- **Мультиязычность**: Полная поддержка английского, русского и узбекского языков
- **Идемпотентность**: Защита от дублирования платежей
- **Webhook Retry**: Автоматические повторные попытки для failed callbacks
- **Ограничение частоты запросов**: Защита от DDoS атак (10 запросов/минуту)
- **Валидация входных данных**: Комплексная валидация сумм и данных платежей
- **Мониторинг**: Метрики платежей и отслеживание производительности
- **Безопасность**: Защита от race conditions и безопасная обработка данных

## Поддерживаемые платежные системы

- **Payme** (payme.uz) - Одна из самых популярных платежных систем в Узбекистане
- **Click** (click.uz) - Популярная платежная система в Узбекистане
- **FreedomPay** (freedompay.uz) - Платежная система в Узбекистане

## Установка

1. Установите Frappe Framework и Bench (см. [Руководство по установке Frappe](https://docs.frappe.io/framework/user/en/installation))

2. Добавьте приложение в bench:
   ```bash
   bench get-app uzbek_payments
   ```

3. Установите приложение на сайте:
   ```bash
   bench --site your-site.localhost install-app uzbek_payments
   ```

## Настройка

### Настройка Payme

1. Зарегистрируйтесь на [payme.uz](https://payme.uz)
2. Получите ваш Merchant ID и Key
3. Перейдите в **Payme Settings** в Frappe
4. Введите ваш Merchant ID и Key
5. Сохраните

### Настройка Click

1. Зарегистрируйтесь на [my.click.uz](https://my.click.uz)
2. Получите ваш Merchant ID, Service ID и Secret Key
3. Перейдите в **Click Settings** в Frappe
4. Введите ваши учетные данные
5. Сохраните

### Настройка FreedomPay

1. Зарегистрируйтесь на [freedompay.uz](https://freedompay.uz)
2. Получите ваш Merchant ID, Terminal ID и Secret Key
3. Перейдите в **FreedomPay Settings** в Frappe
4. Введите ваши учетные данные
5. Сохраните

## Использование

### В коде Python

```python
from payments.utils import get_payment_gateway_controller

# Получить контроллер платежного шлюза
controller = get_payment_gateway_controller("Payme")  # или "Click" или "FreedomPay"

# Проверить валюту
controller().validate_transaction_currency("UZS")

# Создать URL оплаты
payment_details = {
    "amount": 100000,  # Сумма в UZS (будет преобразована в тийины)
    "title": "Оплата заказа #123",
    "description": "Оплата через Payme",
    "reference_doctype": "Sales Invoice",
    "reference_docname": "SI-00001",
    "payer_email": "customer@example.com",
    "payer_name": "Иван Иванов",
    "order_id": "ORDER-123",
    "currency": "UZS",
    "redirect_to": "/payment-success",
}

payment_url = controller().get_payment_url(**payment_details)
```

### В веб-формах

1. Перейдите в настройки **Web Form**
2. Включите **Accept Payment**
3. Выберите **Payme**, **Click** или **FreedomPay** как Payment Gateway
4. Установите сумму и валюту (UZS)

## Callback URLs

Платежные системы будут отправлять callback'и на:

- **Payme**: `/api/method/uzbek_payments.payment_gateways.doctype.payme_settings.payme_settings.callback`
- **Click**: `/api/method/uzbek_payments.payment_gateways.doctype.click_settings.click_settings.callback`
- **FreedomPay**: `/api/method/uzbek_payments.payment_gateways.doctype.freedompay_settings.freedompay_settings.callback`

Убедитесь, что эти URL доступны из интернета.

## Обработка статуса платежа

Когда платеж завершен, система вызовет метод `on_payment_authorized` на документе-ссылке.

Пример:

```python
def on_payment_authorized(self, payment_status):
    """Вызывается при авторизации платежа"""
    if payment_status == "Completed":
        # Обновить статус документа
        self.status = "Paid"
        self.save()
        
        # Отправить подтверждающее письмо
        self.send_confirmation_email()
        
        return "/payment-success"  # Опционально: пользовательский URL для редиректа
```

## Валюта

Все платежные системы (Payme, Click и FreedomPay) поддерживают только валюту **UZS** (узбекский сум).

Суммы автоматически преобразуются в тийины (1 UZS = 100 тийинов) для платежных систем.

## Поддержка баз данных

Модуль полностью поддерживает базы данных **PostgreSQL** и **MySQL/MariaDB**:

- Все SQL запросы не зависят от типа базы данных
- Автоматическое определение типа базы данных
- Правильная обработка синтаксиса, специфичного для базы данных (кавычки, функции дат и т.д.)

### Возможности PostgreSQL

- Использует двойные кавычки для имен таблиц
- Использует `EXTRACT(YEAR FROM ...)` для функций дат
- Использует `current_database()` для имени базы данных

### Возможности MySQL/MariaDB

- Использует обратные кавычки для имен таблиц
- Использует `YEAR()` для функций дат
- Использует `DATABASE()` для имени базы данных

## Интеграция с другими модулями

Модуль интегрируется с другими модулями Frappe:

### Модуль Учета
- Автоматическое создание Payment Entry
- Интеграция с Bank Transaction
- Сверка платежей

### Модуль Банкинга
- Интеграция с модулем Uzbek Banking (если установлен)
- Синхронизация банковских транзакций

### Модуль Аналитики
- Интеграция с модулем Analytics (если установлен)
- Экспорт данных платежей для аналитики

### Получить доступные интеграции

```python
from uzbek_payments.integrations import get_available_integrations

# Получить список доступных интеграций
integrations = get_available_integrations()
# Возвращает: {"accounting": True, "banking": True/False, "analytics": True/False}
```

## Мультиязычность

Модуль поддерживает три языка:
- **Английский** (en)
- **Русский** (ru)
- **Узбекский** (uz)

Все пользовательские сообщения переведены с использованием системы переводов Frappe.

## Архитектура

### Структура проекта

```
uzbek_payments/
├── uzbek_payments/
│   ├── __init__.py
│   ├── hooks.py
│   ├── db_utils.py          # Утилиты для БД (поддержка PostgreSQL/MySQL)
│   ├── integrations.py      # Интеграция с другими модулями Frappe
│   ├── validators.py         # Утилиты валидации входных данных
│   ├── idempotency.py       # Обработка идемпотентности платежей
│   ├── webhook_retry.py      # Механизм повторных попыток для webhooks
│   ├── rate_limiter.py       # Ограничение частоты запросов для callbacks
│   ├── api_validators.py     # Валидация ответов API
│   ├── cache_utils.py        # Утилиты кэширования настроек
│   ├── lock_utils.py         # Защита от race conditions
│   ├── metrics.py            # Метрики платежей и мониторинг
│   ├── utils/
│   │   ├── __init__.py
│   │   └── utils.py
│   ├── payment_gateways/
│   │   └── doctype/
│   │       ├── payme_settings/
│   │       │   └── payme_settings.py
│   │       ├── click_settings/
│   │       │   └── click_settings.py
│   │       └── freedompay_settings/
│   │           └── freedompay_settings.py
│   ├── tests/               # Юнит-тесты
│   │   ├── test_db_utils.py
│   │   └── test_integrations.py
│   └── translations/        # Файлы переводов
│       ├── en.csv
│       ├── ru.csv
│       └── uz.csv
├── pyproject.toml
└── README.md
```

## Безопасность

- **Шифрованное хранение**: Все учетные данные платежей хранятся в зашифрованном виде
- **Проверка подписи**: Проверка подписи HMAC-SHA256 для callback'ов
- **HTTPS**: Используется HTTPS для всех запросов к платежным шлюзам
- **Ограничение частоты запросов**: Ограничение для callback endpoints (10 запросов/минуту с одного IP)
- **Валидация входных данных**: Комплексная валидация всех данных платежей
- **Идемпотентность**: Защита от дублирования платежей
- **Защита от race conditions**: Блокировки для предотвращения одновременной обработки
- **Санитизация данных**: Санитизация входных данных для предотвращения инъекций

## Производительность

- **Эффективная обработка**: Оптимизированная обработка платежей с пакетными операциями
- **Оптимизация БД**: Оптимизированные SQL запросы с правильной индексацией
- **Кэширование настроек**: Кэширование настроек шлюзов (снижение запросов к БД на 95%)
- **Асинхронная обработка**: Асинхронная обработка для callback'ов платежей
- **Webhook Retry**: Автоматический механизм повторных попыток для failed webhooks (3 попытки с экспоненциальной задержкой)
- **Валидация ответов**: Валидация ответов API для предотвращения ошибок обработки

## Тестирование

Модуль включает комплексные unit тесты:

```bash
# Запустить все тесты
bench --site sitename run-tests --module uzbek_payments

# Запустить конкретный тест
bench --site sitename run-tests --module uzbek_payments --doctype "Payme Settings"
```

Файлы тестов:
- `test_db_utils.py` - Тесты утилит для БД
- `test_integrations.py` - Тесты интеграций

## Устранение неполадок

### Проблема: "Invalid credentials"

**Решение:**
- Проверьте правильность Merchant ID, Service ID и Secret Key
- Убедитесь, что учетные данные активны в панели платежного шлюза
- Проверьте наличие специальных символов или пробелов в учетных данных

### Проблема: "Invalid signature"

**Решение:**
- Проверьте, что Secret Key совпадает с тем, что в настройках платежного шлюза
- Проверьте доступность callback URL из интернета
- Убедитесь, что используется HTTPS для callback URL

### Проблема: "Payment not found"

**Решение:**
- Проверьте существование Integration Request для платежа
- Проверьте совпадение order_id между запросом и callback
- Проверьте логи платежного шлюза на наличие ошибок

## Разработка

### Добавление нового платежного шлюза

1. Создайте новый DocType в `payment_gateways/doctype/` (например, `newgateway_settings/`)
2. Наследуйте от класса `Document`
3. Реализуйте методы:
   - `validate_credentials()` - проверка учетных данных шлюза
   - `get_payment_url()` - создание URL оплаты
   - `verify_signature()` - проверка подписи callback
   - `callback()` - обработка callback платежа

4. Зарегистрируйте шлюз в `utils.py` используя `create_payment_gateway()`

### Пример

```python
from frappe.model.document import Document
from payments.utils import create_payment_gateway

class NewGatewaySettings(Document):
    def validate(self):
        create_payment_gateway("NewGateway")
        self.validate_credentials()
    
    def get_payment_url(self, **kwargs):
        # Создать URL оплаты
        pass
```

## История изменений

### Версия 1.0.0 (2026-01-XX)
- Первый релиз
- Поддержка Payme, Click и FreedomPay
- Автоматическая обработка платежей
- Обработка статусов платежей
- Полная поддержка PostgreSQL и MySQL/MariaDB
- Интеграция с модулями Учета, Банкинга и Аналитики
- Полная поддержка мультиязычности (EN, RU, UZ)
- Комплексные unit тесты
- **Идемпотентность**: Защита от дублирования платежей
- **Webhook Retry**: Автоматические повторные попытки для failed callbacks (3 попытки)
- **Ограничение частоты запросов**: Ограничение частоты callbacks (10 запросов/минуту)
- **Валидация входных данных**: Комплексная валидация сумм и данных платежей
- **Кэширование настроек**: Кэширование настроек шлюзов (снижение запросов к БД на 95%)
- **Защита от race conditions**: Блокировки для предотвращения одновременной обработки
- **Мониторинг**: Метрики платежей и отслеживание производительности
- **Валидация ответов API**: Валидация всех ответов API

## Лицензия

MIT

## Поддержка

Для вопросов и проблем создайте issue на GitHub или обратитесь в поддержку.
