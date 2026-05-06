from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.utils.hash_utils import hash_password, verify_password
from app.utils.jwt_utils import generate_access_token, generate_refresh_token, verify_access_token, get_jti_from_token
from app.utils.refresh_token_utils import hash_refresh_token
from app.core.cache import cache_service

class AuthService:
    
    @staticmethod
    def register(db: Session, email: str, password: str):
        existing = db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first()
        if existing:
            raise ValueError("Пользователь с таким email уже существует")
        
        password_hash = hash_password(password)
        user = User(email=email, password_hash=password_hash)
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return {"id": user.id, "email": user.email}
    
    @staticmethod
    def login(db: Session, email: str, password: str):
        user = db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first()
        
        if not user or not user.password_hash:
            raise ValueError("Неверный email или пароль")
        
        if not verify_password(password, user.password_hash):
            raise ValueError("Неверный email или пароль")
        
        # Генерация токенов 
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
            cache_key = f"wp:auth:user:{user.id}:access:{jti}"
            cache_service.set(cache_key, "valid", ttl=settings.CACHE_TTL_JWT)
        
        return access_token, refresh_token, {"id": user.id, "email": user.email}
    
    @staticmethod
    def refresh(db: Session, old_refresh_token: str):
        token_hash = hash_refresh_token(old_refresh_token)
        stored_token = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not stored_token:
            raise ValueError("Неверный или истекший refresh token")
        
        stored_token.revoked = True
        db.commit()
        
        new_access_token, new_jti = generate_access_token(stored_token.user_id)
        new_refresh_token = generate_refresh_token()
        new_token_hash = hash_refresh_token(new_refresh_token)
        expires_at = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRES_DAYS)
        
        new_token = RefreshToken(
            user_id=stored_token.user_id,
            token_hash=new_token_hash,
            expires_at=expires_at
        )
        db.add(new_token)
        db.commit()
        
        # Сохраняем новый JTI в Redis
        if cache_service.is_available():
            cache_key = f"wp:auth:user:{stored_token.user_id}:access:{new_jti}"
            cache_service.set(cache_key, "valid", ttl=settings.CACHE_TTL_JWT)
        
        return new_access_token, new_refresh_token
    
    @staticmethod
    def logout(db: Session, refresh_token: str, access_token: str = None):
        """Выход из текущей сессии с удалением JTI из Redis"""
        # Отзыв refresh token в БД
        if refresh_token:
            token_hash = hash_refresh_token(refresh_token)
            token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
            if token:
                token.revoked = True
                db.commit()
        
        # Удаление JTI из Redis (отзыв access token)
        if access_token:
            jti = get_jti_from_token(access_token)
            if jti and cache_service.is_available():
                # Удаляем ключ с этим JTI
                cache_service.delete_pattern(f"*:access:{jti}")
    
    @staticmethod
    def logout_all(db: Session, user_id: int):
        # Отзыв всех refresh токенов в БД
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False
        ).update({"revoked": True})
        db.commit()
        
        # Удаляем все JTI пользователя из Redis
        if cache_service.is_available():
            cache_service.delete_pattern(f"wp:auth:user:{user_id}:access:*")
    
    @staticmethod
    def get_user_from_access_token(db: Session, access_token: str):
        payload = verify_access_token(access_token)
        if not payload:
            return None
        
        user = db.query(User).filter(
            User.id == payload['user_id'],
            User.deleted_at.is_(None)
        ).first()
        
        if not user:
            return None
        
        return {"id": user.id, "email": user.email}
    
    @staticmethod
    def is_token_valid_in_redis(access_token: str) -> bool:
        """Проверка, не отозван ли токен через Redis"""
        jti = get_jti_from_token(access_token)
        if not jti or not cache_service.is_available():
            return True  # Если Redis недоступен, полагаемся только на JWT
        
        # Ищем ключ с этим JTI
        keys = cache_service.client.keys(f"*:access:{jti}")
        return len(keys) > 0
    
    @staticmethod
    def get_user_profile(db: Session, user_id: int):
        """Получение профиля пользователя с кешированием"""
        cache_key = f"wp:users:profile:{user_id}"
        
        # Пробуем из кеша
        cached = cache_service.get(cache_key)
        if cached:
            return cached
        
        # Из БД
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        profile = {"id": user.id, "email": user.email}
        
        # Сохраняем в кеш
        cache_service.set(cache_key, profile, ttl=300)
        
        return profile