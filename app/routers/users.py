import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app.models import User, MedCard
from app.schemas import BaseResponse
from app.dependencies import get_current_user
from app.config import settings
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json

router = APIRouter(prefix="/users", tags=["Users"])


class MedCardUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    emergency_contacts: Optional[List[Dict[str, Any]]] = []
    current_diagnosis: Optional[str] = None
    blood_type: Optional[str] = None
    rhesus_factor: Optional[str] = None
    chronic_diseases: Optional[List[str]] = []
    allergies: Optional[List[str]] = []
    special_features: Optional[str] = None
    medications: Optional[List[Dict[str, Any]]] = []
    home_address: Optional[str] = None

@router.get("/me", response_model=BaseResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Получение информации о текущем пользователе"""
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "id": current_user.id,
            "name": current_user.name,
            "phone": current_user.phone,
            "email": current_user.email if current_user.email else "",
            "role": current_user.role,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None
        }
    )


def decode_medcard_data(data_encrypted: bytes) -> dict:
    """Декодирует данные медкарты из BYTEA"""
    if not data_encrypted:
        return {
            "blood_type": None,
            "allergies": [],
            "chronic": [],
            "contacts": []
        }
    try:
        # Декодируем байты в строку и парсим JSON
        json_str = data_encrypted.decode('utf-8')
        return json.loads(json_str)
    except Exception as e:
        print(f"Error decoding medcard data: {e}")
        return {
            "blood_type": None,
            "allergies": [],
            "chronic": [],
            "contacts": []
        }


def encode_medcard_data(data: dict) -> bytes:
    """Кодирует данные медкарты в BYTEA"""
    # Преобразуем dict в JSON строку, затем в байты
    json_str = json.dumps(data, ensure_ascii=False)
    return json_str.encode('utf-8')


@router.get("/{user_id}/medcard", response_model=BaseResponse)
async def get_medcard(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение медкарты пользователя"""
    
    # ОБНОВЛЁННАЯ ПРОВЕРКА ПРАВ ДОСТУПА
    has_access = False
    
    # 1. Свою медкарту может смотреть владелец
    if current_user.id == user_id:
        has_access = True
    
    # 2. Операторы и админы видят все медкарты
    elif current_user.role in ['operator', 'admin']:
        has_access = True
    
    # 3. НОВОЕ: Волонтёры могут смотреть медкарты своих пациентов
    elif current_user.role == 'volunteer':
        # Проверяем есть ли активная заявка между волонтёром и этим пользователем
        from app.models import Volunteer, Booking
        
        # Находим ID волонтёра в таблице volunteers
        volunteer_result = await db.execute(
            select(Volunteer).where(Volunteer.user_id == current_user.id)
        )
        volunteer = volunteer_result.scalar_one_or_none()
        
        if volunteer:
            # Проверяем есть ли заявка от этого пользователя к этому волонтёру
            booking_result = await db.execute(
                select(Booking).where(
                    and_(
                        Booking.user_id == user_id,
                        Booking.volunteer_id == volunteer.id
                    )
                )
            )
            booking = booking_result.scalar_one_or_none()
            
            if booking:
                has_access = True
                print(f"✅ Volunteer {current_user.id} has access to medcard of user {user_id} via booking {booking.id}")
            else:
                print(f"❌ Volunteer {current_user.id} has no bookings with user {user_id}")
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Остальной код без изменений
    result = await db.execute(
        select(MedCard).where(MedCard.user_id == user_id)
    )
    medcard = result.scalar_one_or_none()
    
    if not medcard:
        # Создаём пустую медкарту
        default_data = {
            "full_name": None,
            "age": None,
            "home_address": None,
            "emergency_contacts": [],
            "current_diagnosis": None,
            "blood_type": None,
            "rhesus_factor": None,
            "chronic_diseases": [],
            "allergies": [],
            "special_features": None,
            "medications": [],
        }
        medcard = MedCard(
            user_id=user_id,
            data_encrypted=encode_medcard_data(default_data)
        )
        db.add(medcard)
        await db.commit()
        await db.refresh(medcard)
    
    medcard_data = decode_medcard_data(medcard.data_encrypted)
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "medcard_id": medcard.id,
            "user_id": medcard.user_id,
            "data": medcard_data
        }
    )

@router.patch("/{user_id}/medcard", response_model=BaseResponse)
async def update_medcard(
    user_id: int,
    medcard_data: MedCardUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновление медкарты пользователя"""
    
    if current_user.id != user_id and current_user.role not in ['operator', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    result = await db.execute(
        select(MedCard).where(MedCard.user_id == user_id)
    )
    medcard = result.scalar_one_or_none()
    
    # Формируем данные - ПРИНИМАЕМ ВСЕ ПОЛЯ
    data = {
        "full_name": medcard_data.full_name,
        "age": medcard_data.age,
        "emergency_contacts": medcard_data.emergency_contacts,
        "current_diagnosis": medcard_data.current_diagnosis,
        "blood_type": medcard_data.blood_type,
        "rhesus_factor": medcard_data.rhesus_factor,
        "chronic_diseases": medcard_data.chronic_diseases,
        "allergies": medcard_data.allergies,
        "special_features": medcard_data.special_features,
        "medications": medcard_data.medications,
        "home_address": medcard_data.home_address,
    }
    
    # Кодируем в байты
    encoded_data = encode_medcard_data(data)
    
    if medcard:
        medcard.data_encrypted = encoded_data
    else:
        medcard = MedCard(
            user_id=user_id,
            data_encrypted=encoded_data
        )
        db.add(medcard)
    
    await db.commit()
    await db.refresh(medcard)
    
    response_data = decode_medcard_data(medcard.data_encrypted)
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "medcard_id": medcard.id,
            "user_id": medcard.user_id,
            "data": response_data,
            "message": "Medcard updated successfully"
        }
    )


@router.get("/{user_id}", response_model=BaseResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение информации о пользователе"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "id": user.id,
            "name": user.name,
            "phone": user.phone,
            "email": user.email if user.email else "",
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    )

@router.put("/me/photo")
async def update_user_photo(
    photo_url: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновление фотографии пользователя"""
    
    current_user.photo_url = photo_url
    current_user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(current_user)
    
    return {
        "status": "ok",
        "message": "Photo updated",
        "photo_url": current_user.photo_url
    }
