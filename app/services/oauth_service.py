import httpx
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from urllib.parse import urlencode
from app.core.config import settings
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.utils.jwt_utils import generate_access_token, generate_refresh_token
from app.utils.refresh_token_utils import hash_refresh_token
from app.core.cache import cache_service

class OAuthService:
    
    @staticmethod
    def get_yandex_auth_url(state: str) -> str:
        """Формирование URL для перенаправления на Яндекс OAuth"""
        params = {
            'response_type': 'code',
            'client_id': settings.YANDEX_CLIENT_ID,
            'redirect_uri': settings.YANDEX_CALLBACK_URL,
            'state': state
        }
        return f"{settings.YANDEX_AUTHORIZE_URL}?{urlencode(params)}"
    
    @staticmethod
    async def handle_yandex_callback(db: Session, code: str, state: str, stored_state: str):
        """Обработка callback от Яндекса"""
        # Проверка state (защита от CSRF)
        if not stored_state or state != stored_state:
            raise ValueError("Invalid state parameter")
        
        async with httpx.AsyncClient() as client:
            # Обмен code на access_token
            token_response = await client.post(
                settings.YANDEX_TOKEN_URL,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'client_id': settings.YANDEX_CLIENT_ID,
                    'client_secret': settings.YANDEX_CLIENT_SECRET,
                }
            )
            token_data = token_response.json()
            
            if 'access_token' not in token_data:
                raise ValueError("Failed to get access token from Yandex")
            
            # Получение данных пользователя
            user_response = await client.get(
                settings.YANDEX_USERINFO_URL,
                params={'format': 'json'},
                headers={'Authorization': f'OAuth {token_data["access_token"]}'}
            )
            user_data = user_response.json()
        
        # Поиск или создание пользователя
        user = db.query(User).filter(User.yandex_id == str(user_data.get('id'))).first()
        
        if not user:
            user = User(
                email=user_data.get('default_email', f"yandex_{user_data['id']}@yandex.ru"),
                yandex_id=str(user_data['id'])
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Генерация токенов (РАСПАКОВЫВАЕМ КОРТЕЖ!)
        access_token, jti = generate_access_token(user.id)
        refresh_token = generate_refresh_token()
        refresh_token_hash = hash_refresh_token(refresh_token)
        expires_at = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRES_DAYS)
        
        # Сохраняем Refresh Token в БД
        new_token = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at
        )
        db.add(new_token)
        db.commit()
        
        # Сохраняем JTI в Redis для возможности отзыва токена
        if cache_service.is_available():
            cache_service.set(
                f"wp:auth:user:{user.id}:access:{jti}",
                "valid",
                ttl=settings.CACHE_TTL_JWT
            )
        
        return access_token, refresh_token, user