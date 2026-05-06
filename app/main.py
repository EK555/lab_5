from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core.config import settings
from app.api.routes import auth
from app.api.v1.endpoints import services

app = FastAPI(
    title="SPA Salon API",
    description="""
    ## RESTful API для управления услугами SPA-салона

    ### Возможности API:
    - **Аутентификация и авторизация** (JWT токены, HttpOnly cookies)
    - **OAuth 2.0** вход через Яндекс (Yandex ID)
    - **CRUD операции** для управления услугами
    - **Пагинация** и мягкое удаление (soft delete)

    ### Технологии:
    - FastAPI, PostgreSQL, SQLAlchemy, Alembic
    - JWT, bcrypt, OAuth 2.0
    - Docker, Docker Compose

    ### Контакты:
    - Студент: Бондаренко Екатерина Антоновна
    - Группа: 020303-АИСа-о23
    - Преподаватель: Шестериков Дмитрий Валерьевич
    """,
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router)
app.include_router(services.router)

# Корневой эндпоинт
@app.get("/")
async def root():
    return {"message": "SPA Salon API", "docs": "/api/docs"}

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy"}

# Кастомная OpenAPI схема с примерами ошибок
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Добавляем схему безопасности для JWT через Cookie
    openapi_schema["components"]["securitySchemes"] = {
        "CookieAuth": {
            "type": "apiKey",
            "in": "cookie",
            "name": "access_token",
            "description": "JWT токен, который устанавливается после входа через /auth/login или OAuth. Автоматически отправляется браузером."
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Альтернативный способ авторизации через Bearer токен. В проекте используется HttpOnly cookie."
        },
        "OAuth2Yandex": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://oauth.yandex.ru/authorize",
                    "tokenUrl": "https://oauth.yandex.ru/token",
                    "scopes": {
                        "login:email": "Доступ к email",
                        "login:info": "Доступ к логину, имени и фамилии"
                    }
                }
            }
        }
    }
    
    # Указываем, какие эндпоинты требуют авторизации
    # (это добавит иконку замка в Swagger UI)
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if path.startswith("/api/v1/services") or path.startswith("/auth/logout") or path.startswith("/auth/whoami") or path.startswith("/auth/refresh"):
                openapi_schema["paths"][path][method]["security"] = [{"CookieAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi