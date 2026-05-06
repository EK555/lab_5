# SPA Salon API

RESTful API для управления услугами SPA-салона с системой аутентификации и авторизации на основе JWT токенов. Реализовано на FastAPI с использованием PostgreSQL, SQLAlchemy, Alembic.

## Функциональность

### Лабораторная работа №2
- CRUD операции для услуг (создание, чтение, обновление, удаление)
- Пагинация списка услуг
- Мягкое удаление (soft delete)
- Валидация данных
- Автоматическая документация Swagger UI

### Лабораторная работа №3
- Регистрация и вход пользователей
- JWT аутентификация (Access Token + Refresh Token)
- Хеширование паролей с солью (bcrypt)
- HttpOnly cookies для безопасной передачи токенов
- Защита CRUD эндпоинтов через middleware
- Выход из системы (logout и logout-all)
- Обновление токенов через refresh token

### Лабораторная работа №4
- Автоматическая документация API (Swagger UI / OpenAPI)
- Документация доступна только в режиме разработки (`/api/docs`)
- Интерактивное тестирование эндпоинтов через Swagger UI
- Авторизация в Swagger через JWT токены
- Примеры запросов и ответов для всех эндпоинтов

### Лабораторная работа №5
- Кеширование списка услуг в Redis (TTL 300 секунд)
- Инвалидация кеша при создании, обновлении и удалении услуг
- Хранение JTI (JWT ID) в Redis для мгнового отзыва Access токенов
- Проверка JTI в middleware при каждом запросе

## Запуск через Docker

### 1. Клонируйте репозиторий
```bash
git clone https://github.com/yakunenkova/lab3.git
cd lab3
```
### 2. Создайте файл переменных окружения
```bash
cp .env.example .env
```
### 3. Запустите приложение
```bash
docker-compose up --build
```
## Локальный запуск (без Docker)

### 1. Запустить PostgreSQL в Docker
```bash
docker-compose up -d postgres
```
### 2. Создать виртуальное окружение
```bash
python -m venv .venv
.venv\Scripts\activate
```
### 3. Установить зависимости
```bash
pip install -r requirements.txt
```
### 4. Применить миграции
```bash
alembic upgrade head
```
### 5. Запустить сервер
```bash
uvicorn app.main:app --reload
```
## Переменные окружения (.env.example)
```env
# База данных
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=spa_db
DB_HOST=postgres
DB_PORT=5432
PORT=8000
APP_NAME="SPA Salon API"
ENVIRONMENT=development

# JWT настройки
JWT_ACCESS_SECRET=supersecretaccesstokenkey1234567890
JWT_REFRESH_SECRET=supersecretrefreshtokenkey0987654321
JWT_ACCESS_EXPIRES_MINUTES=15
JWT_REFRESH_EXPIRES_DAYS=7

# OAuth (Yandex/VK)
YANDEX_CLIENT_ID=your_client_id_here
YANDEX_CLIENT_SECRET=your_client_secret_here
YANDEX_CALLBACK_URL=http://localhost:8000/auth/oauth/yandex/callback
O_AUTH_STATE_SECRET=random_string_for_state_encryption

# Redis настройки
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_secure_password_change_in_prod
CACHE_TTL_DEFAULT=300
CACHE_TTL_JWT=900
```
## API Эндпоинты

### Документация API

Проект использует автоматическую документацию OpenAPI (Swagger).

| Режим | Доступность | URL |
|-------|-------------|-----|
| **Development** |  Доступна | `http://localhost:8000/api/docs` |
| **Development** |  Доступна | `http://localhost:8000/api/redoc` |
| **Production** |  Недоступна (404) | — |

### Особенности документации:
- Все эндпоинты сгруппированы по тегам: `Authentication`, `services`
- Для каждого эндпоинта указаны возможные коды ответов (200, 201, 400, 401, 403, 404, 409)
- Приведены примеры запросов и ответов
- Защищённые эндпоинты отмечены значком замка 🔒
- Поддерживается тестирование через интерфейс Swagger UI

### Аутентификация (Лабораторная работа №3)

| Метод | URL | Описание | Доступ |
|-------|-----|----------|--------|
| POST | `/auth/register` | Регистрация пользователя | Public |
| POST | `/auth/login` | Вход (установка cookies) | Public |
| POST | `/auth/refresh` | Обновление токенов | Public |
| GET | `/auth/whoami` | Проверка статуса аутентификации | Private |
| POST | `/auth/logout` | Выход из текущей сессии | Private |
| POST | `/auth/logout-all` | Выход со всех устройств | Private |

### Услуги (Лабораторная работа №2)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/services?page=1&limit=10` | Получить список услуг (с пагинацией) |
| GET | `/api/v1/services/{id}` | Получить услугу по ID |
| POST | `/api/v1/services` | Создать новую услугу |
| PUT | `/api/v1/services/{id}` | Полностью обновить услугу |
| PATCH | `/api/v1/services/{id}` | Частично обновить услугу |
| DELETE | `/api/v1/services/{id}` | Мягкое удаление услуги |

 Важно: Все эндпоинты /api/v1/services/* защищены аутентификацией. Требуется валидный Access Token в cookies.

 ## Кеширование (Redis)

### Как работает кеширование:

| Ключ кеша | Данные | TTL | Инвалидация |
|-----------|--------|-----|-------------|
| `wp:services:list:page:{page}:limit:{limit}` | Список услуг с пагинацией | 300 сек | POST, PUT, PATCH, DELETE |
| `wp:auth:user:{id}:access:{jti}` | JTI Access токена | 900 сек | Logout, Logout-all |

### Проверка кеша через Redis CLI

```bash
# Подключиться к Redis
docker exec -it fastapi_spa_redis redis-cli --pass redis_secure_password_change_in_prod

# Посмотреть все ключи
KEYS 'wp:*'

# Получить значение ключа списка услуг
GET wp:services:list:page:1:limit:10
```

### Параметры пагинации
| Параметр | Значение по умолчанию | Допустимый диапазон |
|----------|----------------------|---------------------|
| `page` | 1 | от 1 и выше |
| `limit` | 10 | от 1 до 100 |

### Примеры запросов

## Аутентификация
1. Регистрация пользователя
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "12345678"
  }'
```
Ожидаемый ответ:
json
{
  "message": "Пользователь успешно зарегистрирован"
}

2. Вход (логин)
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "12345678"
  }' \
  -c cookies.txt
```
Ожидаемый ответ:
json
{
  "message": "Вход выполнен успешно",
  "user": {
    "id": 1,
    "email": "user@example.com"
  }
}

3. Проверка статуса аутентификации
```bash
curl -X GET http://localhost:8000/auth/whoami -b cookies.txt
```
Ожидаемый ответ:
json
{
  "user": {
    "id": 1,
    "email": "user@example.com"
  }
}

4. Обновление токенов
```bash
curl -X POST http://localhost:8000/auth/refresh -b cookies.txt -c cookies.txt
```
Ожидаемый ответ:
json
{
  "message": "Токены обновлены"
}

5. Выход из системы
```bash
curl -X POST http://localhost:8000/auth/logout -b cookies.txt
```
Ожидаемый ответ:
json
{
  "message": "Выход выполнен"
}

## Услуги (требуется аутентификация)
1. Создание услуги
```bash
curl -X POST http://localhost:8000/api/v1/services \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Массаж спины",
    "description": "Расслабляющий массаж спины",
    "duration": 60,
    "price": 2500,
    "category": "massage",
    "status": "active"
  }' \
  -b cookies.txt
```
2. Получение списка с пагинацией
```bash
curl -X GET "http://localhost:8000/api/v1/services?page=1&limit=10" -b cookies.txt
```
Ожидаемый ответ:
json
{
  "data": [
    {
      "id": 1,
      "name": "Массаж спины",
      "description": "Расслабляющий массаж спины",
      "duration": 60,
      "price": 2500,
      "category": "massage",
      "status": "active",
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-01T12:00:00"
    }
  ],
  "meta": {
    "total": 1,
    "page": 1,
    "limit": 10,
    "total_pages": 1
  }
}

3. Получение услуги по ID
```bash
curl -X GET http://localhost:8000/api/v1/services/1 -b cookies.txt
```
4. Частичное обновление услуги (PATCH)
```bash
curl -X PATCH http://localhost:8000/api/v1/services/1 \
  -H "Content-Type: application/json" \
  -d '{"price": 3000}' \
  -b cookies.txt
```
5. Полное обновление услуги (PUT)
```bash
curl -X PUT http://localhost:8000/api/v1/services/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Массаж спины премиум",
    "description": "Глубокий массаж спины",
    "duration": 90,
    "price": 3500,
    "category": "massage",
    "status": "active"
  }' \
  -b cookies.txt
```
6. Удаление услуги (soft delete)
```bash
curl -X DELETE http://localhost:8000/api/v1/services/1 -b cookies.txt
```
### Кеширование (проверка через Redis)

```bash
# После GET /services проверьте Redis
docker exec -it fastapi_spa_redis redis-cli --pass redis_secure_password_change_in_prod KEYS 'wp:*'

# Должен появиться ключ: wp:services:list:page:1:limit:10
```

### Безопасность
-	Пароли хешируются с использованием bcrypt (уникальная соль для каждого пароля)
-	Access и Refresh токены передаются через HttpOnly cookies
-	Refresh токены хранятся в БД в хешированном виде
-	Access Token живёт 15 минут, Refresh Token — 7 дней
-	Реализована защита от CSRF через параметр state (для OAuth)
-	Soft delete для сохранения истории
- JTI (JWT ID) хранятся в Redis для мгновенного отзыва Access токенов
- Redis защищён паролем
- Ключи кеша имеют префиксы `wp:` для избежания конфликтов

### Миграции базы данных
```bash
# Создать новую миграцию
alembic revision --autogenerate -m "описание"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```
### Документация API
После запуска приложения документация доступна по адресам:
-	Swagger UI: http://localhost:8000/api/docs
-	ReDoc: http://localhost:8000/api/redoc

