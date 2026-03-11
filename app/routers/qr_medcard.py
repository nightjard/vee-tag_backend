# app/routers/qr_medcard.py

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import qrcode
import secrets
import io
from datetime import datetime

from app.database import get_db
from app.models import User, MedCard
from app.schemas import BaseResponse
from app.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/qr", tags=["QR Medcard"])

def generate_permanent_token(user_id: int) -> str:
    """
    Генерация ПОСТОЯННОГО токена для пользователя
    Формат: user_id (8 цифр) + случайная строка (16 символов)
    Пример: 00000042-X3j7kP9mQ2nL5tRv
    """
    random_suffix = secrets.token_urlsafe(16)
    return f"{user_id:08d}-{random_suffix}"

async def get_or_create_qr_token(user_id: int, db: AsyncSession) -> str:
    """
    Получить существующий токен или создать новый
    Токен сохраняется в поле qr_token таблицы users
    """
    # Получаем пользователя
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Если токен уже существует - возвращаем его
    if user.qr_token:
        print(f"✅ Using existing QR token for user {user_id}: {user.qr_token[:20]}...")
        return user.qr_token
    
    # Создаём новый токен
    new_token = generate_permanent_token(user_id)
    user.qr_token = new_token
    
    await db.commit()
    await db.refresh(user)
    
    print(f"✅ Created new QR token for user {user_id}: {new_token[:20]}...")
    return new_token


def extract_user_id_from_token(token: str) -> int | None:
    """Извлечение user_id из токена"""
    try:
        user_id_str = token.split('-')[0]
        return int(user_id_str)
    except:
        return None


@router.get("/medcard/{user_id}", response_model=BaseResponse)
async def get_medcard_qr_info(
    user_id: int,
    x_api_key: str = Header(..., alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Получение информации о QR коде"""
    # Проверка API ключа
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    # Проверяем что пользователь существует
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Генерируем токен
    token = await get_or_create_qr_token(user_id, db)
    base_url = "http://localhost:8000"
    medcard_url = f"{base_url}/api/v1/qr/view/{token}"
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "user_id": user_id,
            "token": token,
            "url": medcard_url,
            "qr_image_url": f"{base_url}/api/v1/qr/image/{token}",
            "message": "QR code info retrieved successfully"
        }
    )


@router.get("/image/{token}")
async def get_qr_image(token: str):
    """Генерация изображения QR кода"""
    
    # Проверяем что токен валидный
    user_id = extract_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format"
        )
    
    # Генерируем QR код с URL медкарты
    base_url = "http://localhost:8000"
    medcard_url = f"{base_url}/api/v1/qr/view/{token}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(medcard_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Конвертируем в байты
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return StreamingResponse(img_io, media_type="image/png")


@router.get("/view/{token}", response_class=HTMLResponse)
async def view_medcard_by_qr(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Публичная страница медкарты по токену
    Доступна всем, кто знает ссылку
    """
    
    # Извлекаем user_id из токена
    user_id = extract_user_id_from_token(token)
    if not user_id:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Ошибка - Pozily</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
                .error { color: #d32f2f; font-size: 24px; margin: 20px; }
            </style>
        </head>
        <body>
            <h1>⚠️ Ошибка</h1>
            <p class="error">Неверная ссылка</p>
            <p>Проверьте правильность ссылки или QR кода</p>
        </body>
        </html>
        """
    
    # Получаем пользователя
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Ошибка - Pozily</title>
        </head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>⚠️ Пользователь не найден</h1>
        </body>
        </html>
        """
    
    # Получаем медкарту
    result = await db.execute(
        select(MedCard).where(MedCard.user_id == user_id)
    )
    medcard = result.scalar_one_or_none()
    
    if not medcard:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Медкарта - {user.name}</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: white;
                }}
            </style>
        </head>
        <body>
            <h1>🏥 {user.name}</h1>
            <p>Медицинская карта не заполнена</p>
        </body>
        </html>
        """
    
    # Декодируем медкарту
    from app.routers.users import decode_medcard_data
    medcard_data = decode_medcard_data(medcard.data_encrypted)
    
    # Формируем HTML страницу (упрощённая версия)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Медкарта - {medcard_data.get('full_name', user.name)}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
            .header p {{ opacity: 0.9; font-size: 14px; }}
            .content {{ padding: 30px; }}
            .section {{
                margin-bottom: 30px;
                padding-bottom: 30px;
                border-bottom: 1px solid #e0e0e0;
            }}
            .section:last-child {{ border-bottom: none; }}
            .section-title {{
                font-size: 20px;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 15px;
            }}
            .info-row {{
                display: flex;
                margin-bottom: 10px;
                padding: 10px;
                background: #f5f5f5;
                border-radius: 8px;
            }}
            .info-label {{
                font-weight: bold;
                color: #666;
                min-width: 150px;
            }}
            .info-value {{ color: #333; flex: 1; }}
            .blood-type {{
                display: inline-block;
                background: #f44336;
                color: white;
                padding: 10px 20px;
                border-radius: 25px;
                font-size: 24px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .emergency-contact {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin-bottom: 10px;
                border-radius: 8px;
            }}
            .emergency-contact strong {{
                color: #ff6f00;
                font-size: 18px;
            }}
            .list-item {{
                padding: 10px;
                background: #e3f2fd;
                margin-bottom: 8px;
                border-radius: 8px;
                border-left: 4px solid #2196f3;
            }}
            .warning {{
                background: #ffebee;
                border: 2px solid #f44336;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }}
            .warning strong {{ color: #d32f2f; }}
            @media print {{
                body {{ background: white; }}
                .container {{ box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏥 МЕДИЦИНСКАЯ КАРТА</h1>
                <p>Vee-tag - Платформа помощи пожилым</p>
            </div>
            
            <div class="content">
                <div class="warning">
                    <strong>⚠️ КОНФИДЕНЦИАЛЬНО</strong><br>
                    Эта информация предназначена только для экстренных служб и медицинского персонала
                </div>
                
                <!-- Основная информация -->
                <div class="section">
                    <div class="section-title">▸ Основная информация</div>
                    <div class="info-row">
                        <div class="info-label">ФИО:</div>
                        <div class="info-value">{medcard_data.get('full_name', 'Не указано')}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Возраст:</div>
                        <div class="info-value">{medcard_data.get('age', 'Не указан')} лет</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Адрес:</div>
                        <div class="info-value">{medcard_data.get('home_address', 'Не указан')}</div>
                    </div>
                </div>
                
                <!-- Группа крови -->
                {f'''
                <div class="section">
                    <div class="section-title">▸ Группа крови</div>
                    <div class="blood-type">
                        🩸 {medcard_data.get('blood_type', '?')} ({medcard_data.get('rhesus_factor', '?')})
                    </div>
                </div>
                ''' if medcard_data.get('blood_type') else ''}
                
                <!-- Экстренные контакты -->
                {f'''
                <div class="section">
                    <div class="section-title">▸ 🚨 Экстренные контакты</div>
                    {''.join([f"""
                    <div class="emergency-contact">
                        <strong>{'🔴' if c.get('priority') == 1 else '🟠' if c.get('priority') == 2 else '🔵'} 
                        {c.get('name', 'Не указано')}</strong>
                        {f" ({c.get('relation')})" if c.get('relation') else ''}<br>
                        📞 <a href="tel:{c.get('phone', '')}">{c.get('phone', 'Не указан')}</a>
                    </div>
                    """ for c in medcard_data.get('emergency_contacts', [])])}
                </div>
                ''' if medcard_data.get('emergency_contacts') else ''}
                
                <!-- Диагноз -->
                {f'''
                <div class="section">
                    <div class="section-title">▸ Текущий диагноз</div>
                    <div class="info-value">{medcard_data.get('current_diagnosis')}</div>
                </div>
                ''' if medcard_data.get('current_diagnosis') else ''}
                
                <!-- Хронические заболевания -->
                {f'''
                <div class="section">
                    <div class="section-title">▸ Хронические заболевания</div>
                    {''.join([f'<div class="list-item">• {disease}</div>' for disease in medcard_data.get('chronic_diseases', [])])}
                </div>
                ''' if medcard_data.get('chronic_diseases') else ''}
                
                <!-- Аллергии -->
                {f'''
                <div class="section">
                    <div class="section-title">▸ 🚫 АЛЛЕРГИИ</div>
                    {''.join([f'<div class="list-item" style="background: #ffebee; border-color: #f44336;">⚠️ {allergy}</div>' for allergy in medcard_data.get('allergies', [])])}
                </div>
                ''' if medcard_data.get('allergies') else ''}
                
                <!-- Лекарства -->
                {f'''
                <div class="section">
                    <div class="section-title">▸ 💊 Принимаемые лекарства</div>
                    {''.join([f"""
                    <div style="background: #e8f5e9; padding: 15px; margin-bottom: 10px; border-radius: 8px; border-left: 4px solid #4caf50;">
                        <strong style="font-size: 16px;">{med.get('name', 'Не указано')}</strong><br>
                        <small>
                            💊 Дозировка: {med.get('dosage', 'Не указана')}<br>
                            ⏰ Частота: {med.get('frequency', 'Не указана')}
                            {f"<br>ℹ️ {med.get('notes')}" if med.get('notes') else ''}
                        </small>
                    </div>
                    """ for med in medcard_data.get('medications', [])])}
                </div>
                ''' if medcard_data.get('medications') else ''}
                
                <!-- Особенности -->
                {f'''
                <div class="section">
                    <div class="section-title">▸ ℹ️ Индивидуальные особенности</div>
                    <div class="info-value">{medcard_data.get('special_features')}</div>
                </div>
                ''' if medcard_data.get('special_features') else ''}
                
                <div style="text-align: center; color: #999; font-size: 12px; margin-top: 30px;">
                    <p>Страница доступна по постоянной ссылке</p>
                    <p>Обновлено: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


@router.get("/by-phone", response_model=BaseResponse)
async def get_user_by_phone(
    phone: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
):
    """Получение пользователя по номеру (для админки)"""
    
    # СНАЧАЛА проверяем API ключ
    if x_api_key:
        if x_api_key != settings.ADMIN_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key"
            )
        # API ключ валидный - продолжаем
    else:
        # Нет API ключа - требуем JWT
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header required"
        )
    
    result = await db.execute(
        select(User).where(User.phone == phone)
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
            "email": user.email or "",
            "role": user.role
        }
    )

@router.post("/verify/{user_id}")
async def verify_volunteer(
    user_id: int,
    verified: bool = True,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
):
    """Верификация волонтёра"""

    if x_api_key:
        if x_api_key != settings.ADMIN_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header required"
        )
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    volunteer = result.scalar_one_or_none()
    
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if volunteer.role != 'volunteer':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only volunteers can be verified"
        )
    
    # Просто обновляем is_verified, БЕЗ updated_at
    volunteer.is_verified = verified
    
    await db.commit()
    await db.refresh(volunteer)
    
    return {
        "status": "ok",
        "message": f"Volunteer {'verified' if verified else 'unverified'}",
        "volunteer_id": volunteer.id,
        "is_verified": volunteer.is_verified
    }