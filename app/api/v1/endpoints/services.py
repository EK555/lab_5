from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import math

from app.core.database import get_db
from app.services.service_service import ServiceService
from app.schemas.service import ServiceResponse, ServiceCreate, ServiceUpdate
from app.schemas.pagination import PaginatedResponse
from app.middleware.auth import authenticate

router = APIRouter(prefix="/services", tags=["services"])


@router.get(
    "/",
    response_model=PaginatedResponse[ServiceResponse],
    responses={
        200: {"description": "Список услуг успешно получен", "model": PaginatedResponse[ServiceResponse]},
        401: {"description": "Не авторизован (отсутствует или истёк токен)"}
    },
    summary="Получить список услуг",
    description="Возвращает список всех услуг с пагинацией. Только для авторизованных пользователей."
)
def get_services(
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=100, description="Количество записей на странице (макс. 100)"),
    db: Session = Depends(get_db),
    _: bool = Depends(authenticate)
):
    services, total = ServiceService.get_services(db, page, limit)
    total_pages = math.ceil(total / limit) if total > 0 else 1

    return PaginatedResponse(
        data=services,
        meta={
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    )


@router.get(
    "/{service_id}",
    response_model=ServiceResponse,
    responses={
        200: {"description": "Услуга успешно найдена", "model": ServiceResponse},
        401: {"description": "Не авторизован (отсутствует или истёк токен)"},
        404: {"description": "Услуга с указанным ID не найдена"}
    },
    summary="Получить услугу по ID",
    description="Возвращает данные конкретной услуги. Только для авторизованных пользователей."
)
def get_service(
    service_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(authenticate)
):
    service = ServiceService.get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.post(
    "/",
    response_model=ServiceResponse,
    status_code=201,
    responses={
        201: {"description": "Услуга успешно создана", "model": ServiceResponse},
        401: {"description": "Не авторизован (отсутствует или истёк токен)"},
        422: {"description": "Ошибка валидации данных (неверный формат поля)"}
    },
    summary="Создать новую услугу",
    description="Создаёт новую услугу. Только для авторизованных пользователей."
)
def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(authenticate)
):
    return ServiceService.create_service(db, service)


@router.put(
    "/{service_id}",
    response_model=ServiceResponse,
    responses={
        200: {"description": "Услуга успешно обновлена", "model": ServiceResponse},
        401: {"description": "Не авторизован (отсутствует или истёк токен)"},
        403: {"description": "Нет прав на редактирование (можно редактировать только свои услуги)"},
        404: {"description": "Услуга с указанным ID не найдена"}
    },
    summary="Полное обновление услуги",
    description="Заменяет все данные услуги. Только для авторизованных пользователей."
)
def update_service(
    service_id: int,
    service: ServiceCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(authenticate)
):
    updated = ServiceService.update_service(db, service_id, ServiceUpdate(**service.dict()))
    if not updated:
        raise HTTPException(status_code=404, detail="Service not found")
    return updated


@router.patch(
    "/{service_id}",
    response_model=ServiceResponse,
    responses={
        200: {"description": "Услуга успешно обновлена", "model": ServiceResponse},
        401: {"description": "Не авторизован (отсутствует или истёк токен)"},
        403: {"description": "Нет прав на редактирование (можно редактировать только свои услуги)"},
        404: {"description": "Услуга с указанным ID не найдена"}
    },
    summary="Частичное обновление услуги",
    description="Обновляет только указанные поля услуги. Только для авторизованных пользователей."
)
def patch_service(
    service_id: int,
    service: ServiceUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(authenticate)
):
    updated = ServiceService.update_service(db, service_id, service)
    if not updated:
        raise HTTPException(status_code=404, detail="Service not found")
    return updated


@router.delete(
    "/{service_id}",
    status_code=204,
    responses={
        204: {"description": "Услуга успешно удалена (soft delete)"},
        401: {"description": "Не авторизован (отсутствует или истёк токен)"},
        403: {"description": "Нет прав на удаление (можно удалять только свои услуги)"},
        404: {"description": "Услуга с указанным ID не найдена"}
    },
    summary="Мягкое удаление услуги",
    description="Помечает услугу как удалённую (устанавливает deleted_at). Только для авторизованных пользователей."
)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(authenticate)
):
    deleted = ServiceService.soft_delete_service(db, service_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Service not found")
    return None