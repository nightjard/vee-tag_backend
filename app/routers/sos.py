from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from geoalchemy2.elements import WKTElement
from app.database import get_db
from app.models import SOSEvent, Device, User, NotificationLog
from app.schemas import (
    SOSCreateRequest, SOSCreateResponse,
    SOSDetailResponse, SOSAckRequest, BaseResponse
)
from app.dependencies import get_current_user, get_current_operator
from typing import List

router = APIRouter(prefix="/sos", tags=["SOS Events"])


@router.post("", response_model=BaseResponse)
async def create_sos_event(
    sos_data: SOSCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Создание SOS события от устройства"""
    # Проверяем идемпотентность - если event_id уже существует
    result = await db.execute(
        select(SOSEvent).where(SOSEvent.event_id == sos_data.event_id)
    )
    existing_event = result.scalar_one_or_none()
    
    if existing_event:
        return BaseResponse(
            status="ok",
            code=200,
            data={
                "event_id": str(existing_event.event_id),
                "sos_id": existing_event.id,
                "status": existing_event.status,
                "notified": True
            }
        )
    
    # Получаем устройство
    device_result = await db.execute(
        select(Device).where(Device.device_id == sos_data.device_id)
    )
    device = device_result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Создаем геометрию точки (PostGIS)
    point = WKTElement(f'POINT({sos_data.lon} {sos_data.lat})', srid=4326)
    
    # Создаем событие SOS
    new_sos = SOSEvent(
        event_id=sos_data.event_id,
        device_id=device.id,
        user_id=device.user_id,
        geom=point,
        accuracy_m=sos_data.accuracy_m,
        timestamp=sos_data.timestamp,
        status='new',
        payload={
            "battery_percent": sos_data.battery_percent,
            "signal_type": sos_data.signal_type,
            "sos_type": sos_data.sos_type,
            "additional": sos_data.additional
        }
    )
    
    db.add(new_sos)
    await db.commit()
    await db.refresh(new_sos)
    
    # TODO: Здесь должна быть логика отправки уведомлений
    # Для MVP создаем заглушку в notifications_log
    notification = NotificationLog(
        sos_event_id=new_sos.id,
        recipient="system",
        channel="push",
        delivered=False,
        attempts=0
    )
    db.add(notification)
    await db.commit()
    
    return BaseResponse(
        status="ok",
        code=201,
        data={
            "event_id": str(new_sos.event_id),
            "sos_id": new_sos.id,
            "status": new_sos.status,
            "notified": False
        }
    )


@router.get("/{sos_id}", response_model=BaseResponse)
async def get_sos_event(
    sos_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение детальной информации о SOS событии"""
    result = await db.execute(
        select(SOSEvent).where(SOSEvent.id == sos_id)
    )
    sos_event = result.scalar_one_or_none()
    
    if not sos_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SOS event not found"
        )
    
    # Получаем пользователя
    user_result = await db.execute(
        select(User).where(User.id == sos_event.user_id)
    )
    user = user_result.scalar_one_or_none()
    
    # Получаем устройство
    device_result = await db.execute(
        select(Device).where(Device.id == sos_event.device_id)
    )
    device = device_result.scalar_one_or_none()
    
    # Извлекаем координаты из geom
    lat = sos_event.payload.get("lat", 0.0) if sos_event.payload else 0.0
    lon = sos_event.payload.get("lon", 0.0) if sos_event.payload else 0.0
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "sos_id": sos_event.id,
            "event_id": str(sos_event.event_id),
            "device_id": device.device_id if device else None,
            "user": {
                "id": user.id if user else None,
                "name": user.name if user else None,
                "phone": user.phone if user else None
            },
            "lat": lat,
            "lon": lon,
            "accuracy_m": sos_event.accuracy_m,
            "timestamp": sos_event.timestamp,
            "status": sos_event.status,
            "actions": []  # TODO: добавить историю действий
        }
    )


@router.post("/{sos_id}/ack", response_model=BaseResponse)
async def acknowledge_sos(
    sos_id: int,
    ack_data: SOSAckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Подтверждение получения SOS уведомления"""
    result = await db.execute(
        select(SOSEvent).where(SOSEvent.id == sos_id)
    )
    sos_event = result.scalar_one_or_none()
    
    if not sos_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SOS event not found"
        )
    
    # Обновляем статус
    await db.execute(
        update(SOSEvent)
        .where(SOSEvent.id == sos_id)
        .values(status='acknowledged')
    )
    await db.commit()
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "sos_id": sos_id,
            "status": "acknowledged"
        }
    )


@router.get("", response_model=BaseResponse)
async def list_sos_events(
    limit: int = 50,
    status_filter: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение списка SOS событий"""
    query = select(SOSEvent).order_by(SOSEvent.timestamp.desc()).limit(limit)
    
    if status_filter:
        query = query.where(SOSEvent.status == status_filter)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    events_data = []
    for event in events:
        # Получаем пользователя
        user_result = await db.execute(
            select(User).where(User.id == event.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        events_data.append({
            "sos_id": event.id,
            "event_id": str(event.event_id),
            "user_name": user.name if user else None,
            "timestamp": event.timestamp,
            "status": event.status
        })
    
    return BaseResponse(
        status="ok",
        code=200,
        data=events_data
    )
