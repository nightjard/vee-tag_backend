from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app.models import Device, User
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
