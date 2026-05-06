from fastapi import APIRouter, Request, Response, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.services.oauth_service import OAuthService
from app.schemas.auth import RegisterRequest, LoginRequest, WhoamiResponse, UserResponse, MessageResponse
from app.utils.oauth_utils import generate_oauth_state

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Хранилище для state параметров (временное, для тестирования)
oauth_states = {}


@router.post(
    "/register", 
    status_code=201, 
    response_model=MessageResponse,
    responses={
        201: {"description": "Пользователь успешно зарегистрирован", "model": MessageResponse},
        400: {"description": "Неверный формат email или пароль"},
        409: {"description": "Пользователь с таким email уже существует"}
    },
    summary="Регистрация нового пользователя",
    description="Создаёт нового пользователя с указанным email и паролем. Пароль хешируется с помощью bcrypt (уникальная соль)."
)
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = AuthService.register(db, data.email, data.password)
        return MessageResponse(message="Пользователь успешно зарегистрирован")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/login",
    response_model=dict,
    responses={
        200: {"description": "Вход выполнен успешно, токены установлены в cookies"},
        401: {"description": "Неверный email или пароль"}
    },
    summary="Вход пользователя",
    description="Проверяет email и пароль, генерирует Access и Refresh токены, устанавливает их в HttpOnly cookies."
)
async def login(response: Response, data: LoginRequest, db: Session = Depends(get_db)):
    try:
        access_token, refresh_token, user = AuthService.login(db, data.email, data.password)
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=15 * 60
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=7 * 24 * 60 * 60
        )
        
        return {"message": "Вход выполнен успешно", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post(
    "/refresh",
    response_model=dict,
    responses={
        200: {"description": "Токены успешно обновлены"},
        401: {"description": "Не предоставлен refresh token или токен недействителен"}
    },
    summary="Обновление токенов",
    description="Использует Refresh Token из cookies для получения новой пары Access и Refresh токенов."
)
async def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get('refresh_token')
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Не предоставлен refresh token")
    
    try:
        new_access_token, new_refresh_token = AuthService.refresh(db, refresh_token)
        
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=15 * 60
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=7 * 24 * 60 * 60
        )
        
        return {"message": "Токены обновлены"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post(
    "/logout",
    response_model=dict,
    responses={
        200: {"description": "Выход выполнен успешно"},
        401: {"description": "Не авторизован"}
    },
    summary="Выход из текущей сессии",
    description="Отзывает текущий Refresh Token и Access Token (через Redis), удаляет cookies."
)
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get('refresh_token')
    access_token = request.cookies.get('access_token')
    
    AuthService.logout(db, refresh_token, access_token)
    
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {"message": "Выход выполнен"}


@router.post(
    "/logout-all",
    response_model=dict,
    responses={
        200: {"description": "Выход со всех устройств выполнен успешно"},
        401: {"description": "Не авторизован"}
    },
    summary="Выход со всех устройств",
    description="Отзывает все Refresh токены текущего пользователя."
)
async def logout_all(request: Request, response: Response, db: Session = Depends(get_db)):
    access_token = request.cookies.get('access_token')
    if access_token:
        user = AuthService.get_user_from_access_token(db, access_token)
        if user:
            AuthService.logout_all(db, user['id'])
    
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {"message": "Выход со всех устройств выполнен"}


@router.get(
    "/whoami",
    response_model=WhoamiResponse,
    responses={
        200: {"description": "Пользователь авторизован", "model": WhoamiResponse},
        401: {"description": "Не авторизован (отсутствует или истёк токен)"}
    },
    summary="Проверка статуса аутентификации",
    description="Возвращает данные текущего пользователя, если Access Token валиден."
)
async def whoami(request: Request, db: Session = Depends(get_db)):
    access_token = request.cookies.get('access_token')
    
    if not access_token:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    user = AuthService.get_user_from_access_token(db, access_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    return WhoamiResponse(user=UserResponse(**user))


# ========== OAuth ЭНДПОИНТЫ ==========

@router.get(
    "/oauth/yandex",
    responses={
        302: {"description": "Перенаправление на страницу авторизации Яндекса"},
        400: {"description": "Ошибка формирования запроса"}
    },
    summary="Инициация входа через Яндекс",
    description="Перенаправляет пользователя на страницу авторизации Яндекса. После успешного входа пользователь возвращается на /docs."
)
async def oauth_yandex():
    """Инициация входа через Яндекс"""
    state = generate_oauth_state()
    oauth_states[state] = state
    auth_url = OAuthService.get_yandex_auth_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/oauth/yandex/callback")
async def oauth_yandex_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    stored_state = oauth_states.get(state)
    try:
        access_token, refresh_token, user = await OAuthService.handle_yandex_callback(
            db, code, state, stored_state
        )
        
        print(f"=== OAuth SUCCESS ===")
        print(f"access_token: {access_token[:50]}...")
        print(f"refresh_token: {refresh_token[:50]}...")
        print(f"user: {user}")
        
        oauth_states.pop(state, None)
        
        response = RedirectResponse(url="/api/docs")
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=15 * 60
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=7 * 24 * 60 * 60
        )
        
        print(f"Cookies set, redirecting to /api/docs")
        
        return response
    except Exception as e:
        print(f"OAuth error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))