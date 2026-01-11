# Тестирование

## Запуск тестов

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Запуск всех тестов

```bash
pytest
```

### Запуск с покрытием кода

```bash
# С HTML отчетом
pytest --cov=app --cov-report=html --cov-report=term

# С XML отчетом (для CI/CD)
pytest --cov=app --cov-report=xml --cov-report=term

# С проверкой минимального покрытия (81%)
pytest --cov=app --cov-report=xml --cov-report=term --cov-fail-under=81
```

### Запуск конкретного теста

```bash
pytest tests/test_auth.py
pytest tests/test_items.py::test_get_items
```

### Просмотр HTML отчета о покрытии

После запуска с `--cov-report=html`, откройте `htmlcov/index.html` в браузере.

## Структура тестов

- `conftest.py` - Фикстуры для тестовой БД и клиента
- `test_*.py` - Основные тесты для каждого модуля
  - `test_auth.py` - Тесты аутентификации
  - `test_items.py` - Тесты товаров
  - `test_cart.py` - Тесты корзины
  - `test_orders.py` - Тесты заказов
  - `test_chat.py` - Тесты чата
  - `test_admin.py` - Тесты админ-панели
  - и другие...
- `test_*_extended.py` - Расширенные тесты с дополнительными сценариями
  - `test_admin_extended.py` - Расширенные тесты админ-панели
  - `test_chat_extended.py` - Расширенные тесты чата
- `test_*_quick.py` - Быстрые тесты для повышения покрытия кода
  - `test_admin_quick.py` - Быстрые тесты админ-панели
  - `test_chat_quick.py` - Быстрые тесты чата
  - `test_api_quick.py` - Быстрые тесты API
  - `test_main_quick.py` - Быстрые тесты main.py
- `test_coverage_boost.py` - Дополнительные тесты для достижения целевого покрытия
- `test_services_*.py` - Тесты сервисного слоя
- `test_websocket.py` - Тесты WebSocket соединений

## Требования к покрытию

Минимальное покрытие кода: **81%**

Если покрытие ниже 81%, тесты не пройдут.

### Исключенные из покрытия файлы

Следующие файлы исключены из расчета покрытия (некритичные утилиты):
- `app/core/cache.py` - Кэширование (не используется в продакшене)
- `app/core/security_utils.py` - Дополнительные утилиты безопасности
- `app/utils/query_analyzer.py` - Анализатор запросов (не используется)
- `app/utils/__init__.py` - Пустой файл
- `app/core/logging.py` - Логирование (низкий приоритет)
- `app/services/notification_service.py` - Уведомления (низкий приоритет)

См. `pytest.ini` для полного списка исключений.

## Добавление новых тестов

1. Создайте файл `test_*.py` в папке `tests/`
2. Используйте фикстуры из `conftest.py`:
   - `client` - AsyncClient для запросов
   - `db_session` - Сессия тестовой БД
   - `test_user`, `test_seller`, `test_admin` - Тестовые пользователи
   - `auth_headers`, `seller_headers`, `admin_headers` - Заголовки авторизации

Пример:

```python
@pytest.mark.asyncio
async def test_my_endpoint(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/my-endpoint", headers=auth_headers)
    assert response.status_code == 200
```

