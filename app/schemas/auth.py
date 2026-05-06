from pydantic import BaseModel, EmailStr, Field, validator

class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com", description="Email пользователя")
    password: str = Field(..., min_length=8, example="12345678", description="Пароль (минимум 8 символов)")
    
    @validator('password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен быть не менее 8 символов')
        return v

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com", description="Email пользователя")
    password: str = Field(..., example="12345678", description="Пароль")

class UserResponse(BaseModel):
    id: int = Field(..., example=1, description="ID пользователя")
    email: EmailStr = Field(..., example="user@example.com", description="Email пользователя")

class MessageResponse(BaseModel):
    message: str = Field(..., example="Операция выполнена успешно", description="Сообщение об успехе")

class WhoamiResponse(BaseModel):
    user: UserResponse

class ErrorResponse(BaseModel):
    detail: str = Field(..., example="Сообщение об ошибке", description="Детали ошибки")