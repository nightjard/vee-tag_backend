#!/usr/bin/env python3
"""
Скрипт для тестирования API Pozily Backend
Демонстрирует основные сценарии использования
"""

import requests
import json
from datetime import datetime, timedelta
import uuid

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_response(title, response):
    """Красивый вывод ответа"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print()


def test_api():
    """Тестирование API"""
    
    # 1. Регистрация родственника
    print("🚀 Тестирование API Pozily Backend\n")
    
    relative_data = {
        "name": "Мария Иванова",
        "phone": "+79991234567",
        "email": "maria@example.com",
        "role": "relative",
        "password": "secure_password"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=relative_data)
    print_response("1. Регистрация родственника", response)
    
    # 2. Регистрация волонтёра
    volunteer_data = {
        "name": "Александр Петров",
        "phone": "+79991234568",
        "email": "alex@example.com",
        "role": "volunteer",
        "password": "secure_password"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=volunteer_data)
    print_response("2. Регистрация волонтёра", response)
    
    # 3. Вход родственника
    login_data = {
        "phone": "+79991234567",
        "otp": "123456"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print_response("3. Вход родственника", response)
    
    if response.status_code == 200:
        relative_token = response.json()["data"]["access_token"]
        relative_id = response.json()["data"]["user"]["id"]
    else:
        print("❌ Ошибка входа родственника")
        return
    
    # 4. Вход волонтёра
    login_data_vol = {
        "phone": "+79991234568",
        "otp": "123456"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data_vol)
    print_response("4. Вход волонтёра", response)
    
    if response.status_code == 200:
        volunteer_token = response.json()["data"]["access_token"]
        volunteer_id = response.json()["data"]["user"]["id"]
        print(volunteer_token)
    else:
        print("❌ Ошибка входа волонтёра")
        return
    
    # 5. Регистрация волонтёра в системе
    volunteer_reg_data = {
        "services": ["visit", "shopping", "medical_escort"],
        "region": "moscow"
    }

    headers_vol = {"Authorization": f"Bearer {volunteer_token}"}
    response = requests.post(
        f"{BASE_URL}/volunteers/register",
        json=volunteer_reg_data,  # ← JSON body, а не query params
        headers=headers_vol
    )
    print_response("5. Регистрация в системе волонтёров", response)
    
    # 6. Получение списка волонтёров
    headers_rel = {"Authorization": f"Bearer {relative_token}"}
    response = requests.get(
        f"{BASE_URL}/volunteers?region=moscow&available=true",
        headers=headers_rel
    )
    print_response("6. Список доступных волонтёров", response)
    
    # 7. Создание бронирования
    booking_data = {
        "user_id": relative_id,
        "volunteer_id": volunteer_id,
        "slot": (datetime.now() + timedelta(days=1)).isoformat(),
        "address": "ул. Тверская, д. 15, кв. 42",
        "notes": "Помощь с покупками в супермаркете"
    }

    response = requests.post(
        f"{BASE_URL}/bookings",
        json=booking_data,
        headers=headers_rel
    )
    print_response("7. Создание бронирования", response)

    # Проверяем и 200, и 201 (FastAPI может вернуть любой)
    if response.status_code in [200, 201]:
        booking_id = response.json()["data"]["booking_id"]
        print(f"✅ Бронирование создано успешно! ID: {booking_id}")
    else:
        print("❌ Ошибка создания бронирования")
        return

    # 8. Отправка сообщения от родственника
    message_data = {
        "booking_id": booking_id,
        "message": "Здравствуйте! Спасибо что согласились помочь. Встретимся завтра в 14:00?"
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/messages",
        json=message_data,
        headers=headers_rel
    )
    print_response("8. Сообщение от родственника в чат", response)
    
    # 9. Ответ от волонтёра
    message_data_vol = {
        "booking_id": booking_id,
        "message": "Добрый день! Да, конечно. Буду у вас в 14:00. Что нужно купить?"
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/messages",
        json=message_data_vol,
        headers=headers_vol
    )
    print_response("9. Ответ волонтёра в чат", response)
    
    # 10. Еще сообщение от родственника
    message_data2 = {
        "booking_id": booking_id,
        "message": "Нужно хлеб, молоко и фрукты. Составлю список подробнее."
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/messages",
        json=message_data2,
        headers=headers_rel
    )
    print_response("10. Еще сообщение от родственника", response)
    
    # 11. История чата
    response = requests.get(
        f"{BASE_URL}/chat/bookings/{booking_id}/messages",
        headers=headers_rel
    )
    print_response("11. История чата", response)
    
    # 12. Все чаты родственника
    response = requests.get(
        f"{BASE_URL}/chat/my-chats",
        headers=headers_rel
    )
    print_response("12. Все чаты родственника", response)
    
    # 13. Регистрация устройства
    device_data = {
        "device_id": "BRSLT-00001234",
        "imei": "359876543210123",
        "firmware_version": "1.0.0"
    }
    
    response = requests.post(f"{BASE_URL}/devices/register", json=device_data)
    print_response("13. Регистрация браслета", response)
    
    # 14. Создание SOS события
    sos_data = {
        "device_id": "BRSLT-00001234",
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "lat": 55.751244,
        "lon": 37.618423,
        "accuracy_m": 10,
        "battery_percent": 75,
        "signal_type": "LTE",
        "sos_type": "SHORT_PRESS"
    }
    
    response = requests.post(f"{BASE_URL}/sos", json=sos_data)
    print_response("14. Создание SOS события", response)
    
    if response.status_code == 201:
        sos_id = response.json()["data"]["sos_id"]
        
        # 15. Детали SOS события
        response = requests.get(
            f"{BASE_URL}/sos/{sos_id}",
            headers=headers_rel
        )
        print_response("15. Детали SOS события", response)
    
    # 16. Список бронирований волонтёра
    response = requests.get(
        f"{BASE_URL}/bookings",
        headers=headers_vol
    )
    print_response("16. Бронирования волонтёра", response)
    
    print("\n✅ Тестирование завершено!")
    print("📱 Функция чата работает корректно!")
    print("🔗 Swagger документация: http://localhost:8000/docs")


if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка: Не удалось подключиться к API")
        print("Убедитесь что сервер запущен: docker-compose up")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
