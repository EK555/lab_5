import secrets
import hmac

def generate_oauth_state() -> str:
    """Генерация случайного state параметра для защиты от CSRF"""
    return secrets.token_urlsafe(32)

def verify_oauth_state(state: str, stored_state: str) -> bool:
    """Проверка state параметра"""
    if not stored_state or not state:
        return False
    return hmac.compare_digest(state, stored_state)