from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ServiceCreate(BaseModel):
    name: str = Field(..., example="Массаж спины", description="Название услуги")
    description: str = Field(..., example="Расслабляющий массаж спины", description="Описание услуги")
    duration: int = Field(..., example=60, ge=1, description="Длительность в минутах")
    price: int = Field(..., example=2500, ge=0, description="Стоимость услуги")
    category: str = Field(..., example="massage", description="Категория услуги")
    status: str = Field(default="active", example="active", description="Статус (active/inactive)")

class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, example="Массаж спины премиум", description="Название услуги")
    description: Optional[str] = Field(None, example="Глубокий расслабляющий массаж", description="Описание услуги")
    duration: Optional[int] = Field(None, example=90, ge=1, description="Длительность в минутах")
    price: Optional[int] = Field(None, example=3500, ge=0, description="Стоимость услуги")
    category: Optional[str] = Field(None, example="massage", description="Категория услуги")
    status: Optional[str] = Field(None, example="active", description="Статус (active/inactive)")

class ServiceResponse(BaseModel):
    id: int = Field(..., example=1)
    name: str = Field(..., example="Массаж спины")
    description: str = Field(..., example="Расслабляющий массаж спины")
    duration: int = Field(..., example=60)
    price: int = Field(..., example=2500)
    category: str = Field(..., example="massage")
    status: str = Field(..., example="active")
    created_at: Optional[datetime] = Field(None, example="2024-01-01T12:00:00")
    updated_at: Optional[datetime] = Field(None, example="2024-01-01T12:00:00")
    deleted_at: Optional[datetime] = Field(None, example=None)