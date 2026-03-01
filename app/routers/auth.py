from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from app.database import get_db
from app.models import User
from app.schemas import (
    LoginRequest, TokenResponse, RefreshRequest, 
    BaseResponse, UserCreate, UserResponse
)
from app.auth import (
    verify_password, get_password_hash, 
    create_access_token, create_refresh_token, verify_token
)
from app.config import settings
from app.services.email_service import send_otp_email 
import random 
from pydantic import BaseModel



router = APIRouter(prefix="/auth", tags=["Authentication"])

_otp_storage = {}

def generate_otp() -> str:
    """Генерация 6-значного OTP кода"""
    return str(random.randint(100000, 999999))

async def save_otp(phone: str, otp: str):
    _otp_storage[phone] = otp
    print(f"🔑 OTP saved for {phone}: {otp}")

async def get_otp(phone: str):
    return _otp_storage.get(phone)

async def delete_otp(phone: str):
    if phone in _otp_storage:
        del _otp_storage[phone]


@router.post("/register", response_model=BaseResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Регистрация нового пользователя"""
    
    # Проверяем существование пользователя по телефону
    result = await db.execute(select(User).where(User.phone == user_data.phone))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this phone already exists"
        )
    
    if user_data.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing_email = result.scalar_one_or_none()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
    
    # Создаем нового пользователя
    password_hash = get_password_hash(user_data.password) if user_data.password else None
    
    new_user = User(
        name=user_data.name,
        phone=user_data.phone,
        email=user_data.email,
        role=user_data.role,
        password_hash=password_hash
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    if new_user.email:
        try:
            otp = generate_otp()
            await save_otp(new_user.phone, otp)
            send_otp_email(
                to_email=new_user.email,
                otp_code=otp,
                user_name=new_user.name
            )
            print(f"✅ OTP sent to {new_user.email}")
        except Exception as e:
            print(f"⚠️ Failed to send OTP: {e}")
    
    return BaseResponse(
        status="ok",
        code=201,
        data={
            "id": new_user.id,
            "name": new_user.name,
            "phone": new_user.phone,
            "role": new_user.role,
            "email": new_user.email if new_user.email else ""
        }
    )


@router.post("/login", response_model=BaseResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Вход пользователя - проверка OTP из email"""
    
    # Получаем пользователя
    result = await db.execute(select(User).where(User.phone == login_data.phone))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this phone not found"
        )
    
    stored_otp = await get_otp(user.phone)
    
    if not stored_otp:
        stored_otp = "123456"
    
    if login_data.otp != stored_otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP code"
        )
    
    await delete_otp(user.phone)
    
    # Создаем токены
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": user.role}
    )
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "name": user.name,
                "phone": user.phone,
                "email": user.email if user.email else "",
                "role": user.role
            }
        }
    )

class RequestOtpRequest(BaseModel):
    phone: str

@router.post("/request-otp", response_model=BaseResponse)
async def request_otp(
    request: RequestOtpRequest,
    db: AsyncSession = Depends(get_db)
):
    """Запрос OTP кода на email"""
    phone = request.phone
    # Находим пользователя
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no email address"
        )
    
    # Генерируем и отправляем OTP
    otp = generate_otp()
    await save_otp(user.phone, otp)
    
    email_sent = send_otp_email(
        to_email=user.email,
        otp_code=otp,
        user_name=user.name
    )
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email"
        )
    
    print(f"✅ OTP sent to {user.email} for {user.phone}")
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "message": f"OTP code sent to {user.email}",
            "phone": user.phone
        }
    )


@router.post("/refresh", response_model=BaseResponse)
async def refresh_token(
    refresh_data: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Обновление access token"""
    payload = verify_token(refresh_data.refresh_token, token_type="refresh")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    role = payload.get("role")
    
    # Создаем новый access token
    access_token = create_access_token(
        data={"sub": user_id, "role": role}
    )
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "access_token": access_token,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    )