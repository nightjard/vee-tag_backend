from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app.models import Device, User
from datetime import datetime
from app.schemas import (
    DeviceRegisterRequest, DeviceRegisterResponse,
    TelemetryRequest, BaseResponse
)

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/register", response_model=BaseResponse)
async def register_device(
    device_data: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Регистрация нового устройства (браслета)"""
    # Проверяем существование устройства
    result = await db.execute(
        select(Device).where(Device.device_id == device_data.device_id)
    )
    existing_device = result.scalar_one_or_none()
    
    if existing_device:
        return BaseResponse(
            status="ok",
            code=200,
            data={
                "device_id": existing_device.device_id,
                "registered": True
            }
        )
    
    # Создаем новое устройство
    new_device = Device(
        device_id=device_data.device_id,
        imei=device_data.imei,
        firmware_version=device_data.firmware_version
    )
    
    db.add(new_device)
    await db.commit()
    await db.refresh(new_device)
    
    return BaseResponse(
        status="ok",
        code=201,
        data={
            "device_id": new_device.device_id,
            "registered": True
        }
    )


@router.post("/{device_id}/telemetry", response_model=BaseResponse)
async def send_telemetry(
    device_id: str,
    telemetry: TelemetryRequest,
    db: AsyncSession = Depends(get_db)
):
    """Отправка телеметрии от устройства"""
    # Получаем устройство
    result = await db.execute(
        select(Device).where(Device.device_id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Обновляем данные устройства
    await db.execute(
        update(Device)
        .where(Device.device_id == device_id)
        .values(
            last_seen=telemetry.timestamp,
            battery_percent=telemetry.battery_percent,
            signal_type=telemetry.signal_type
        )
    )
    await db.commit()
    
    return BaseResponse(
        status="ok",
        code=200,
        data={"accepted": True}
    )


@router.get("/{device_id}", response_model=BaseResponse)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Получение информации об устройстве"""
    result = await db.execute(
        select(Device).where(Device.device_id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "id": device.id,
            "device_id": device.device_id,
            "imei": device.imei,
            "firmware_version": device.firmware_version,
            "last_seen": device.last_seen,
            "battery_percent": device.battery_percent,
            "signal_type": device.signal_type,
            "user_id": device.user_id
        }
    )

@router.post("/{device_id}/assign-user", response_model=BaseResponse)
async def assign_user_to_device(
    device_id: str,
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Привязка устройства к пользователю"""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.user_id = user_id
    db.add(device)
    await db.commit()
    await db.refresh(device)
    
    return BaseResponse(
        status="ok",
        code=200,
        data={"device_id": device.device_id, "user_id": device.user_id}
    )

@router.post("/webhook/traccar", response_model=BaseResponse)
async def traccar_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Получаем JSON от Traccar и записываем в устройство.
    Поддерживаем только часть данных.
    """
    payload = await request.json()
    
    for item in payload:
        device_id = str(item.get("deviceId"))
        attributes = item.get("attributes", {})
        
        result = await db.execute(select(Device).where(Device.device_id == device_id))
        device = result.scalar_one_or_none()
        if not device:
            continue  # можно логировать как неизвестное устройство
        
        device.last_seen = datetime.fromisoformat(item.get("serverTime"))
        device.battery_percent = attributes.get("batteryLevel")
        device.latitude = item.get("latitude")
        device.longitude = item.get("longitude")
        device.speed = item.get("speed")
        device.course = item.get("course")
        
        db.add(device)
    
    await db.commit()
    
    return BaseResponse(status="ok", code=200, data={"processed": len(payload)})