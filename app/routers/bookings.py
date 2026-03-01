from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.database import get_db
from app.models import Booking, User, Volunteer, ChatMessage, Review
from app.schemas import BookingCreateRequest, BaseResponse
from app.dependencies import get_current_user
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from app.services.notification_service import (
    notify_booking_created,
    notify_booking_confirmed,
    notify_booking_completed,
    notification_service
)

router = APIRouter(prefix="/bookings", tags=["Bookings"])

class BookingReportRequest(BaseModel):
    report_text: str
    rating: Optional[int] = None


@router.post("", response_model=BaseResponse)
async def create_booking(
    booking_data: BookingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создание бронирования визита волонтёра"""
    
    # Проверяем что у волонтёра нет активных заявок
    active_bookings_result = await db.execute(
        select(Booking).where(
            and_(
                Booking.volunteer_id == booking_data.volunteer_id,
                Booking.status.in_(['pending', 'confirmed', 'in_progress'])
            )
        )
    )
    active_bookings = active_bookings_result.scalars().all()
    
    if len(active_bookings) >= 3:  # Максимум 3 активная заявка
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Волонтёр уже занят другой заявкой. Пожалуйста, дождитесь её завершения."
        )
    
    # Проверяем VOLUNTEER существует
    volunteer_result = await db.execute(
        select(Volunteer).where(Volunteer.id == booking_data.volunteer_id)
    )
    volunteer = volunteer_result.scalar_one_or_none()
    
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Volunteer with id {booking_data.volunteer_id} not found"
        )
    
    if not volunteer.available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Volunteer is not available"
        )
    
    # Создаем бронирование со статусом PENDING
    new_booking = Booking(
        user_id=booking_data.user_id,
        volunteer_id=booking_data.volunteer_id,
        slot=booking_data.slot,
        address=booking_data.address,
        notes=booking_data.notes,
        status='pending',
        created_at=datetime.utcnow()
    )
    
    db.add(new_booking)
    await db.commit()
    await db.refresh(new_booking)
    
    # Создаём приветственное сообщение
    try:
        welcome_message = ChatMessage(
            booking_id=new_booking.id,
            sender_id=current_user.id,
            message=f"Создана заявка на {new_booking.slot.strftime('%d.%m.%Y %H:%M')}. Адрес: {new_booking.address}. Ожидаем подтверждения волонтёра.",
            timestamp=datetime.utcnow()
        )
        db.add(welcome_message)
        await db.commit()
    except Exception as e:
        print(f"Warning: Could not create welcome message: {e}")

    # Уведомление волонтёру
    try:
        # Получаем user_id волонтёра
        volunteer_user_result = await db.execute(
            select(User).where(User.id == volunteer.user_id)
        )
        volunteer_user = volunteer_user_result.scalar_one_or_none()
        
        if volunteer_user:
            await notify_booking_created(
                db=db,
                volunteer_id=volunteer_user.id,
                booking_id=new_booking.id,
                address=new_booking.address
            )
    except Exception as e:
        print(f"Failed to send notification: {e}")
    
    return BaseResponse(
        status="ok",
        code=201,
        data={
            "booking_id": new_booking.id,
            "status": new_booking.status,
            "message": "Заявка создана и отправлена волонтёру"
        }
    )

@router.get("", response_model=BaseResponse)
async def list_bookings(
    status_filter: Optional[str] = Query(None),
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение списка бронирований - ТОЛЬКО СВОИ!"""
    
    # КРИТИЧНО: Фильтруем по роли
    if current_user.role == 'volunteer':
        # Для волонтёра - находим его ID в таблице volunteers
        volunteer_result = await db.execute(
            select(Volunteer).where(Volunteer.user_id == current_user.id)
        )
        volunteer = volunteer_result.scalar_one_or_none()
        if not volunteer:
            return BaseResponse(status="ok", code=200, data=[])
        
        # Только заявки ГДЕ ОН ВОЛОНТЁР
        query = select(Booking).where(Booking.volunteer_id == volunteer.id)
        
    elif current_user.role == 'relative':
        # Для родственника - только ЕГО заявки
        query = select(Booking).where(Booking.user_id == current_user.id)
        
    elif current_user.role == 'operator':
        # Оператор видит всё
        query = select(Booking)
    else:
        # Другие роли - ничего не видят
        return BaseResponse(status="ok", code=200, data=[])
    
    # Фильтр по статусу
    if status_filter:
        query = query.where(Booking.status == status_filter)
    
    query = query.order_by(Booking.slot.desc()).limit(limit)
    
    result = await db.execute(query)
    bookings = result.scalars().all()
    
    # Формируем ответ
    bookings_data = []
    for booking in bookings:
        # Получаем волонтёра
        volunteer_result = await db.execute(
            select(Volunteer).where(Volunteer.id == booking.volunteer_id)
        )
        volunteer = volunteer_result.scalar_one_or_none()
        
        volunteer_user = None
        if volunteer:
            user_result = await db.execute(
                select(User).where(User.id == volunteer.user_id)
            )
            volunteer_user = user_result.scalar_one_or_none()
        
        # Получаем клиента
        client_result = await db.execute(
            select(User).where(User.id == booking.user_id)
        )
        client = client_result.scalar_one_or_none()
        
        bookings_data.append({
            "id": booking.id,
            "user_id": booking.user_id,
            "volunteer_id": booking.volunteer_id,
            "slot": booking.slot.isoformat(),
            "address": booking.address,
            "notes": booking.notes,
            "status": booking.status,
            "created_at": booking.created_at.isoformat(),
            "volunteer": {
                "id": volunteer.id if volunteer else None,
                "name": volunteer_user.name if volunteer_user else "Unknown"
            } if volunteer else None,
            "user": {
                "id": client.id if client else None,
                "name": client.name if client else "Unknown"
            } if client else None
        })
    
    return BaseResponse(
        status="ok",
        code=200,
        data=bookings_data
    )


@router.patch("/{booking_id}/confirm", response_model=BaseResponse)
async def confirm_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Волонтёр подтверждает заявку"""
    
    # Проверяем что пользователь - волонтёр
    if current_user.role != 'volunteer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only volunteers can confirm bookings"
        )
    
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    volunteer_result = await db.execute(
        select(Volunteer).where(Volunteer.user_id == current_user.id)
    )
    volunteer = volunteer_result.scalar_one_or_none()
    
    if not volunteer or booking.volunteer_id != volunteer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This booking is not assigned to you"
        )
    
    # Подтверждаем
    booking.status = 'confirmed'
    await db.commit()
    
    # Отправляем сообщение в чат
    try:
        message = ChatMessage(
            booking_id=booking_id,
            sender_id=current_user.id,
            message="Заявка подтверждена! Буду в указанное время.",
            timestamp=datetime.utcnow()
        )
        db.add(message)
        await db.commit()
    except Exception as e:
        print(f"Warning: Could not send confirmation message: {e}")

    # Уведомление родственнику
    try:
        client_result = await db.execute(
            select(User).where(User.id == booking.user_id)
        )
        client = client_result.scalar_one_or_none()
        
        if client:
            await notify_booking_confirmed(
                db=db,
                user_id=client.id,
                booking_id=booking_id,
                volunteer_name=current_user.name
            )
    except Exception as e:
        print(f"Failed to send notification: {e}")
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "booking_id": booking_id,
            "status": "confirmed"
        }
    )


@router.patch("/{booking_id}/complete", response_model=BaseResponse)
async def complete_booking(
    booking_id: int,
    report_data: BookingReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Волонтёр завершает заявку с отчётом"""
    
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Проверяем права
    volunteer_result = await db.execute(
        select(Volunteer).where(Volunteer.user_id == current_user.id)
    )
    volunteer = volunteer_result.scalar_one_or_none()
    
    if not volunteer or booking.volunteer_id != volunteer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Завершаем
    booking.status = 'completed'
    await db.commit()
    
    # Отправляем отчёт в чат
    try:
        report_message = ChatMessage(
            booking_id=booking_id,
            sender_id=current_user.id,
            message=f"📋 ОТЧЁТ:\n{report_data.report_text}",
            timestamp=datetime.utcnow()
        )
        db.add(report_message)
        await db.commit()
    except Exception as e:
        print(f"Warning: Could not send report: {e}")

    # Уведомление родственнику
    try:
        await notify_booking_completed(
            db=db,
            user_id=booking.user_id,
            booking_id=booking_id
        )
    except Exception as e:
        print(f"Failed to send notification: {e}")
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "booking_id": booking_id,
            "status": "completed",
            "message": "Отчёт отправлен"
        }
    )


@router.patch("/{booking_id}/approve", response_model=BaseResponse)
async def approve_booking(
    booking_id: int,
    rating: int = Query(ge=1, le=5),
    review_text: str = Query(default=""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Родственник подтверждает выполнение и оставляет отзыв"""
    
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Подтверждаем выполнение
    booking.status = 'done'
    
    # НОВОЕ: Создаём отзыв
    new_review = Review(
        booking_id=booking_id,
        volunteer_id=booking.volunteer_id,
        user_id=current_user.id,
        rating=rating,
        review_text=review_text if review_text else None,
        created_at=datetime.utcnow()
    )
    db.add(new_review)
    
    await db.commit()
    
    # Пересчитываем рейтинг волонтёра на основе ВСЕХ отзывов
    volunteer_result = await db.execute(
        select(Volunteer).where(Volunteer.id == booking.volunteer_id)
    )
    volunteer = volunteer_result.scalar_one_or_none()
    
    if volunteer:
        # Получаем все отзывы волонтёра
        reviews_result = await db.execute(
            select(Review).where(Review.volunteer_id == volunteer.id)
        )
        all_reviews = reviews_result.scalars().all()
        
        if all_reviews:
            # Средний рейтинг = сумма оценок / количество отзывов
            total_rating = sum(review.rating for review in all_reviews)
            avg_rating = total_rating / len(all_reviews)
            
            # Сохраняем как 0-50 (умножаем на 10)
            volunteer.rating = int(avg_rating * 10)
            
            await db.commit()
            
            print(f"✅ Updated volunteer {volunteer.id} rating: {avg_rating:.1f} (based on {len(all_reviews)} reviews)")
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "booking_id": booking_id,
            "status": "done",
            "review_id": new_review.id,
            "message": "Спасибо за отзыв!"
        }
    )

@router.get("/{booking_id}", response_model=BaseResponse)
async def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение информации о бронировании"""
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Проверяем доступ
    if current_user.role == 'volunteer':
        volunteer_result = await db.execute(
            select(Volunteer).where(Volunteer.user_id == current_user.id)
        )
        volunteer = volunteer_result.scalar_one_or_none()
        if not volunteer or booking.volunteer_id != volunteer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role == 'relative':
        if booking.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "id": booking.id,
            "user_id": booking.user_id,
            "volunteer_id": booking.volunteer_id,
            "slot": booking.slot.isoformat(),
            "address": booking.address,
            "notes": booking.notes,
            "status": booking.status,
            "created_at": booking.created_at.isoformat()
        }
    )
