from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.cache import cache_service
from app.services.auth_service import AuthService
from app.utils.jwt_utils import verify_access_token, get_jti_from_token

async def authenticate(request: Request, db: Session = Depends(get_db)):
    access_token = request.cookies.get('access_token')
    
    if not access_token:
        raise HTTPException(status_code=401, detail="Не предоставлен access token")
    
    # 1. Проверяем подпись JWT
    payload = verify_access_token(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Неверный или истекший токен")
    
    # 2. Проверяем JTI в Redis (отозван ли токен)
    jti = payload.get('jti')
    if jti and cache_service.is_available():
        client = cache_service.get_client()
        if client:
            # Ищем ключ с этим JTI
            keys = client.keys(f"*:access:{jti}")
            if not keys:
                raise HTTPException(status_code=401, detail="Токен отозван")
    
    # 3. Получаем пользователя из БД
    user = AuthService.get_user_from_access_token(db, access_token)
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    
    request.state.user = user
    return user