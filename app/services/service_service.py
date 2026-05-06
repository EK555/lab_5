from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Tuple

from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceUpdate
from app.core.cache import cache_service


class ServiceService:

    @staticmethod
    def create_service(db: Session, service_data: ServiceCreate) -> Service:
        db_service = Service(
            name=service_data.name,
            description=service_data.description,
            duration=service_data.duration,
            price=service_data.price,
            category=service_data.category,
            status=service_data.status
        )
        db.add(db_service)
        db.commit()
        db.refresh(db_service)
        
        # Инвалидация кеша списков после создания
        cache_service.delete_pattern("wp:services:list:*")
        
        return db_service

    @staticmethod
    def get_service(db: Session, service_id: int) -> Optional[Service]:
        # Пробуем получить из кеша
        cache_key = f"wp:services:item:{service_id}"
        cached = cache_service.get(cache_key)
        
        if cached:
            # Если в кеше есть данные, возвращаем их
            return cached
        
        # Если нет в кеше — запрос к БД
        db_service = db.query(Service).filter(
            Service.id == service_id,
            Service.deleted_at.is_(None)
        ).first()
        
        # Сохраняем в кеш, если найдено
        if db_service:
            cache_service.set(cache_key, db_service, ttl=300)
        
        return db_service

    @staticmethod
    def get_services(db: Session, page: int = 1, limit: int = 10) -> Tuple[List[Service], int]:
        cache_key = f"wp:services:list:page:{page}:limit:{limit}"
        
        cached = cache_service.get(cache_key)
        if cached:
            # Восстанавливаем объекты Service из словарей
            services = []
            for item in cached["services"]:
                services.append(Service(
                    id=item["id"],
                    name=item["name"],
                    description=item["description"],
                    duration=item["duration"],
                    price=item["price"],
                    category=item["category"],
                    status=item["status"],
                    created_at=datetime.fromisoformat(item["created_at"]) if item.get("created_at") else None,
                    updated_at=datetime.fromisoformat(item["updated_at"]) if item.get("updated_at") else None,
                    deleted_at=datetime.fromisoformat(item["deleted_at"]) if item.get("deleted_at") else None
                ))
            return services, cached["total"]
        
        query = db.query(Service).filter(Service.deleted_at.is_(None))
        total = query.count()
        services = query.offset((page - 1) * limit).limit(limit).all()
        
        # Сохраняем как JSON-совместимые словари
        cache_service.set(cache_key, {
            "services": [{
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "duration": s.duration,
                "price": s.price,
                "category": s.category,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "deleted_at": s.deleted_at.isoformat() if s.deleted_at else None
            } for s in services],
            "total": total
        }, ttl=300)
        
        return services, total

    @staticmethod
    def update_service(db: Session, service_id: int, service_data: ServiceUpdate) -> Optional[Service]:
        db_service = db.query(Service).filter(
            Service.id == service_id,
            Service.deleted_at.is_(None)
        ).first()
        if not db_service:
            return None

        update_data = service_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_service, field, value)

        db.commit()
        db.refresh(db_service)
        
        # Инвалидация кеша после обновления
        cache_service.delete(f"wp:services:item:{service_id}")
        cache_service.delete_pattern("wp:services:list:*")
        
        # Сохраняем обновлённые данные в кеш
        cache_service.set(f"wp:services:item:{service_id}", db_service, ttl=300)
        
        return db_service

    @staticmethod
    def soft_delete_service(db: Session, service_id: int) -> bool:
        db_service = db.query(Service).filter(
            Service.id == service_id,
            Service.deleted_at.is_(None)
        ).first()
        if not db_service:
            return False

        db_service.deleted_at = datetime.utcnow()
        db.commit()
        
        # Инвалидация кеша после удаления
        cache_service.delete(f"wp:services:item:{service_id}")
        cache_service.delete_pattern("wp:services:list:*")
        
        return True