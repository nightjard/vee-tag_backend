# app/routers/notifications.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app.models import Notification, User
from app.schemas import BaseResponse
from app.dependencies import get_current_user
from app.services.notification_service import notification_service
from datetime import timezone

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=BaseResponse)
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение списка уведомлений"""
    
    query = select(Notification).where(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.where(Notification.read == False)
    
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    # Форматируем ответ
    notifications_data = [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "data": n.data,
            "read": n.read,
            "created_at": n.created_at.replace(tzinfo=timezone.utc).isoformat()
        }
        for n in notifications
    ]
    
    # Количество непрочитанных
    unread_result = await db.execute(
        select(Notification).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.read == False
            )
        )
    )
    unread_count = len(unread_result.scalars().all())
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "notifications": notifications_data,
            "unread_count": unread_count,
            "total": len(notifications_data)
        }
    )


@router.patch("/{notification_id}/read", response_model=BaseResponse)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Отметить уведомление как прочитанное"""
    
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id
            )
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    await notification_service.mark_as_read(db, notification_id)
    
    return BaseResponse(
        status="ok",
        code=200,
        data={"message": "Notification marked as read"}
    )


@router.post("/mark-all-read", response_model=BaseResponse)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Отметить все уведомления как прочитанные"""
    
    await notification_service.mark_all_as_read(db, current_user.id)
    
    return BaseResponse(
        status="ok",
        code=200,
        data={"message": "All notifications marked as read"}
    )


@router.get("/unread-count", response_model=BaseResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить количество непрочитанных уведомлений"""
    
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.read == False
            )
        )
    )
    unread_count = len(result.scalars().all())
    
    return BaseResponse(
        status="ok",
        code=200,
        data={"unread_count": unread_count}
    )