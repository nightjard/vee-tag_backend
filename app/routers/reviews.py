from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Review, User, Volunteer
from app.schemas import BaseResponse
from app.dependencies import get_current_user
from datetime import timezone

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("/volunteer/{volunteer_id}", response_model=BaseResponse)
async def get_volunteer_reviews(
    volunteer_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Получение всех отзывов волонтёра"""
    
    # Проверяем существует ли волонтёр
    volunteer_result = await db.execute(
        select(Volunteer).where(Volunteer.id == volunteer_id)
    )
    volunteer = volunteer_result.scalar_one_or_none()
    
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer not found"
        )
    
    # Получаем отзывы
    result = await db.execute(
        select(Review)
        .where(Review.volunteer_id == volunteer_id)
        .order_by(Review.created_at.desc())
        .limit(limit)
    )
    reviews = result.scalars().all()
    
    # Форматируем ответ
    reviews_data = []
    for review in reviews:
        # Получаем имя автора отзыва
        user_result = await db.execute(
            select(User).where(User.id == review.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        reviews_data.append({
            "id": review.id,
            "booking_id": review.booking_id,
            "rating": review.rating,
            "review_text": review.review_text,
            "author_name": user.name if user else "Аноним",
            "created_at": review.created_at.replace(tzinfo=timezone.utc).isoformat()
        })
    
    # Статистика
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        rating_distribution = {i: 0 for i in range(1, 6)}
        for r in reviews:
            rating_distribution[r.rating] += 1
    else:
        avg_rating = 0
        rating_distribution = {i: 0 for i in range(1, 6)}
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "reviews": reviews_data,
            "statistics": {
                "total_reviews": len(reviews),
                "average_rating": round(avg_rating, 2),
                "rating_distribution": rating_distribution
            }
        }
    )


@router.get("/booking/{booking_id}", response_model=BaseResponse)
async def get_booking_review(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение отзыва по заявке"""
    
    result = await db.execute(
        select(Review).where(Review.booking_id == booking_id)
    )
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Получаем автора
    user_result = await db.execute(
        select(User).where(User.id == review.user_id)
    )
    user = user_result.scalar_one_or_none()
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "id": review.id,
            "booking_id": review.booking_id,
            "rating": review.rating,
            "review_text": review.review_text,
            "author_name": user.name if user else "Аноним",
            "created_at": review.created_at.replace(tzinfo=timezone.utc).isoformat()
        }
    )