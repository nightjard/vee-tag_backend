from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app.models import Volunteer, User
from app.schemas import VolunteerResponse, BaseResponse, VolunteerRegisterRequest
from app.dependencies import get_current_user
from typing import Optional

router = APIRouter(prefix="/volunteers", tags=["Volunteers"])


@router.get("", response_model=BaseResponse)
async def list_volunteers(
    region: Optional[str] = None,
    service: Optional[str] = None,
    available: Optional[bool] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Получение списка волонтёров с фильтрацией"""
    # Базовый запрос
    query = select(Volunteer).join(User, Volunteer.user_id == User.id)
    
    # Применяем фильтры
    if region:
        query = query.where(Volunteer.region == region)
    
    if available is not None:
        query = query.where(Volunteer.available == available)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    volunteers = result.scalars().all()
    
    volunteers_data = []
    for vol in volunteers:
        # Получаем пользователя
        user_result = await db.execute(
            select(User).where(User.id == vol.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        # Фильтруем по сервису если указан
        if service:
            if vol.services and service not in vol.services:
                continue
        
        volunteers_data.append({
            "id": vol.id,
            "user_id": vol.user_id,
            "name": user.name if user else "Unknown",
            "rating": vol.rating / 10.0,  # Конвертируем в float
            "services": vol.services if vol.services else [],
            "region": vol.region,
            "available": vol.available,
            "next_available": None  # TODO: вычислять из bookings
        })
    
    return BaseResponse(
        status="ok",
        code=200,
        data=volunteers_data
    )


@router.get("", response_model=BaseResponse)
async def get_volunteers(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Получение списка волонтёров"""
    
    try:
        result = await db.execute(
            select(Volunteer, User)
            .join(User, Volunteer.user_id == User.id)
            .limit(limit)
        )
        rows = result.all()
        
        volunteers_data = []
        for volunteer, user in rows:
            volunteers_data.append({
                "id": user.id,
                "volunteer_id": volunteer.id,
                "user_id": volunteer.user_id,
                "name": user.name,
                "phone": user.phone,
                "email": user.email or "",
                "photo_url": user.photo_url or "",
                "is_verified": user.is_verified,
                "rating": float(volunteer.rating) if volunteer.rating else 0.0,
                "services": volunteer.services or [],
                "region": volunteer.region or "",
                "available": volunteer.available
            })
        
        return BaseResponse(
            status="ok",
            code=200,
            data=volunteers_data
        )
    
    except Exception as e:
        print(f"❌ Error loading volunteers: {e}")
        import traceback
        traceback.print_exc()
        
        return BaseResponse(
            status="error",
            code=500,
            data=[],
            error={"message": str(e)}
        )


@router.post("/register", response_model=BaseResponse)
async def register_as_volunteer(
    volunteer_data: VolunteerRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Регистрация пользователя как волонтёра"""
    # Проверяем что пользователь имеет роль volunteer
    if current_user.role != 'volunteer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must have volunteer role"
        )
    
    # Проверяем что волонтёр еще не зарегистрирован
    existing_result = await db.execute(
        select(Volunteer).where(Volunteer.user_id == current_user.id)
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Volunteer already registered"
        )
    
    # Создаем запись волонтёра
    new_volunteer = Volunteer(
        user_id=current_user.id,
        rating=50,  # Начальный рейтинг 5.0
        services=volunteer_data.services,  # ← Из схемы
        region=volunteer_data.region,      # ← Из схемы
        available=True
    )
    
    db.add(new_volunteer)
    await db.commit()
    await db.refresh(new_volunteer)
    
    return BaseResponse(
        status="ok",
        code=201,
        data={
            "volunteer_id": new_volunteer.id,
            "user_id": new_volunteer.user_id,
            "registered": True
        }
    )


@router.patch("/{volunteer_id}/availability", response_model=BaseResponse)
async def update_availability(
    volunteer_id: int,
    available: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновление доступности волонтёра"""
    result = await db.execute(
        select(Volunteer).where(Volunteer.id == volunteer_id)
    )
    volunteer = result.scalar_one_or_none()
    
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer not found"
        )
    
    # Проверяем права - только сам волонтёр или оператор
    if volunteer.user_id != current_user.id and current_user.role not in ['operator', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    volunteer.available = available
    await db.commit()
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "volunteer_id": volunteer_id,
            "available": available
        }
    )
