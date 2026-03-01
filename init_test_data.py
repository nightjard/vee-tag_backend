#!/usr/bin/env python3
"""
Скрипт для инициализации тестовых данных в БД
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models import Base, User, Device, Volunteer
from app.auth import get_password_hash
import os

# Подключение к БД
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://pozily_user:pozily_password_2024@localhost:5432/pozily_db"
)

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_test_data():
    """Инициализация тестовых данных"""
    
    async with async_session_maker() as session:
        print("🔄 Создание тестовых пользователей...")
        
        # Создаем родственников
        relatives = [
            User(
                name="Мария Иванова",
                phone="+79991111111",
                email="maria@example.com",
                role="relative",
                password_hash=get_password_hash("password123")
            ),
            User(
                name="Дмитрий Смирнов",
                phone="+79992222222",
                email="dmitry@example.com",
                role="relative",
                password_hash=get_password_hash("password123")
            ),
        ]
        
        # Создаем волонтёров
        volunteers_users = [
            User(
                name="Александр Петров",
                phone="+79993333333",
                email="alex@example.com",
                role="volunteer",
                password_hash=get_password_hash("password123")
            ),
            User(
                name="Ольга Сидорова",
                phone="+79994444444",
                email="olga@example.com",
                role="volunteer",
                password_hash=get_password_hash("password123")
            ),
            User(
                name="Екатерина Новикова",
                phone="+79995555555",
                email="kate@example.com",
                role="volunteer",
                password_hash=get_password_hash("password123")
            ),
        ]
        
        # Создаем операторов
        operators = [
            User(
                name="Оператор Системы",
                phone="+79996666666",
                email="operator@pozily.com",
                role="operator",
                password_hash=get_password_hash("operator123")
            ),
        ]
        
        # Добавляем всех пользователей
        all_users = relatives + volunteers_users + operators
        session.add_all(all_users)
        await session.commit()
        
        print(f"✅ Создано {len(all_users)} пользователей")
        
        # Создаем волонтёрские профили
        print("🔄 Создание профилей волонтёров...")
        
        volunteers = [
            Volunteer(
                user_id=volunteers_users[0].id,
                rating=48,  # 4.8
                services=["visit", "shopping"],
                region="moscow",
                available=True
            ),
            Volunteer(
                user_id=volunteers_users[1].id,
                rating=50,  # 5.0
                services=["visit", "medical_escort", "shopping"],
                region="moscow",
                available=True
            ),
            Volunteer(
                user_id=volunteers_users[2].id,
                rating=45,  # 4.5
                services=["visit"],
                region="saint_petersburg",
                available=True
            ),
        ]
        
        session.add_all(volunteers)
        await session.commit()
        
        print(f"✅ Создано {len(volunteers)} профилей волонтёров")
        
        # Создаем устройства
        print("🔄 Создание тестовых устройств...")
        
        devices = [
            Device(
                device_id="BRSLT-00001",
                user_id=relatives[0].id,
                imei="359876543210001",
                firmware_version="1.0.0",
                battery_percent=85,
                signal_type="LTE"
            ),
            Device(
                device_id="BRSLT-00002",
                user_id=relatives[1].id,
                imei="359876543210002",
                firmware_version="1.0.0",
                battery_percent=92,
                signal_type="LTE"
            ),
        ]
        
        session.add_all(devices)
        await session.commit()
        
        print(f"✅ Создано {len(devices)} устройств")
        
        print("\n" + "="*60)
        print("✅ Инициализация тестовых данных завершена!")
        print("="*60)
        print("\nТестовые учетные записи:")
        print("\n📱 Родственники:")
        print("  - Телефон: +79991111111, OTP: 123456 (Мария Иванова)")
        print("  - Телефон: +79992222222, OTP: 123456 (Дмитрий Смирнов)")
        print("\n🤝 Волонтёры:")
        print("  - Телефон: +79993333333, OTP: 123456 (Александр Петров)")
        print("  - Телефон: +79994444444, OTP: 123456 (Ольга Сидорова)")
        print("  - Телефон: +79995555555, OTP: 123456 (Екатерина Новикова)")
        print("\n👨‍💼 Операторы:")
        print("  - Телефон: +79996666666, OTP: 123456 (Оператор)")
        print("\n📟 Устройства:")
        print("  - BRSLT-00001 (Мария Иванова)")
        print("  - BRSLT-00002 (Дмитрий Смирнов)")
        print("\n🔑 OTP для всех: 123456")
        print("="*60 + "\n")


async def main():
    """Главная функция"""
    print("\n" + "="*60)
    print("🚀 Инициализация тестовых данных Pozily Backend")
    print("="*60 + "\n")
    
    try:
        await init_test_data()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
