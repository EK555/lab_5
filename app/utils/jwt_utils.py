import uuid
import jwt
from datetime import datetime, timedelta
import secrets
from app.core.config import settings

def generate_jti() -> str:
    """Генерация уникального идентификатора токена (JTI)"""
    return str(uuid.uuid4())

def generate_access_token(user_id: int) -> tuple[str, str]:
    """
    Генерирует Access Token и возвращает (токен, jti)
    """
    jti = generate_jti()
    expires_minutes = int(settings.JWT_ACCESS_EXPIRES_MINUTES)
    payload = {
        'user_id': user_id,
        'type': 'access',
        'jti': jti,
        'exp': datetime.utcnow() + timedelta(minutes=expires_minutes),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm='HS256')
    return token, jti

def generate_refresh_token() -> str:
    """Генерация Refresh Token"""
    return secrets.token_urlsafe(64)

def verify_access_token(token: str) -> dict | None:
    """Проверка Access Token"""
    try:
        return jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=['HS256'])
    except:
        return None

def get_jti_from_token(token: str) -> str | None:
    """Извлечь JTI из токена"""
    payload = verify_access_token(token)
    if payload:
        return payload.get('jti')
    return None