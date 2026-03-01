from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models import User
from app.auth import verify_token
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Получение текущего пользователя из токена"""
    
    # 1. Получаем токен из заголовка
    token = credentials.credentials
    logger.info("Authorization header token: %s", token[:50] + "...")  # Логируем только начало
    
    # 2. Проверяем и декодируем токен
    payload = verify_token(token, token_type="access")
    logger.info("Decoded payload: %s", payload)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Извлекаем user_id из payload (sub может быть строкой)
    sub = payload.get("sub")
    try:
        user_id = int(sub) if sub is not None else None
    except (ValueError, TypeError):
        logger.exception("Invalid 'sub' claim type: %r", sub)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    # 4. Ищем пользователя в БД
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    logger.info("Authenticated user: id=%s, name=%s, role=%s", user.id, user.name, user.role)
    return user

async def get_current_relative(current_user: User = Depends(get_current_user)) -> User:
    """Проверка что пользователь - родственник"""
    if current_user.role != "relative":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_operator(current_user: User = Depends(get_current_user)) -> User:
    """Проверка что пользователь - оператор"""
    if current_user.role != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_volunteer(current_user: User = Depends(get_current_user)) -> User:
    """Проверка что пользователь - волонтёр"""
    if current_user.role != "volunteer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
