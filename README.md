# Pozily Backend API

Backend система для помощи и отслеживания состояния пожилых людей.

## Технологический стек

- **Python 3.11**
- **FastAPI** - веб-фреймворк
- **PostgreSQL 15 + PostGIS** - база данных
- **SQLAlchemy 2.0** - ORM
- **Docker & Docker Compose** - контейнеризация
- **Redis** - кэширование (подготовлено, не используется в MVP)

## Основные функции

1. **Аутентификация и авторизация** (JWT токены)
2. **Управление устройствами** (браслеты)
3. **SOS события** с геолокацией (PostGIS)
4. **Бронирование волонтёров**
5. **Чат между волонтёром и клиентом** 
6. **Уведомления** (заглушка для MVP)

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Git

### Запуск проекта

1. Клонируйте репозиторий или скопируйте файлы

2. Создайте файл `.env` (уже создан, можете изменить значения):
```bash
cp .env.example .env  # если нужно
```

3. Запустите все сервисы через Docker Compose:
```bash
docker-compose up --build
```

4. Подождите пока контейнеры запустятся. API будет доступен по адресу:
- **API**: http://localhost:8000
- **Swagger документация**: http://localhost:8000/docs
- **ReDoc документация**: http://localhost:8000/redoc

### Проверка работы

```bash
curl http://localhost:8000/health
```

Должен вернуть:
```json
{
  "status": "ok",
  "service": "Pozily Backend API",
  "version": "1.0.0"
}
```

## Структура проекта

```
pozily-backend/
├── app/
│   ├── routers/           # API эндпоинты
│   │   ├── auth.py        # Аутентификация
│   │   ├── devices.py     # Устройства (браслеты)
│   │   ├── sos.py         # SOS события
│   │   ├── bookings.py    # Бронирования
│   │   ├── chat.py        # Чат (волонтёр-клиент) 
│   │   └── volunteers.py  # Волонтёры
│   ├── models.py          # SQLAlchemy модели
│   ├── schemas.py         # Pydantic схемы
│   ├── database.py        # Подключение к БД
│   ├── config.py          # Конфигурация
│   ├── auth.py            # JWT утилиты
│   ├── dependencies.py    # FastAPI dependencies
│   └── main.py            # Главный файл приложения
├── docker-compose.yml     # Docker Compose конфигурация
├── Dockerfile             # Docker образ приложения
├── requirements.txt       # Python зависимости
├── .env                   # Переменные окружения
└── README.md             # Этот файл
```

## API Endpoints

### Аутентификация

- `POST /api/v1/auth/register` - Регистрация пользователя
- `POST /api/v1/auth/login` - Вход (OTP упрощен для MVP - используйте "123456")
- `POST /api/v1/auth/refresh` - Обновление токена

### Устройства

- `POST /api/v1/devices/register` - Регистрация браслета
- `POST /api/v1/devices/{device_id}/telemetry` - Отправка телеметрии
- `GET /api/v1/devices/{device_id}` - Информация об устройстве

### SOS События

- `POST /api/v1/sos` - Создание SOS события
- `GET /api/v1/sos/{sos_id}` - Детали SOS события
- `POST /api/v1/sos/{sos_id}/ack` - Подтверждение SOS
- `GET /api/v1/sos` - Список SOS событий

### Бронирования

- `POST /api/v1/bookings` - Создать бронирование
- `GET /api/v1/bookings/{booking_id}` - Детали бронирования
- `GET /api/v1/bookings` - Список бронирований
- `PATCH /api/v1/bookings/{booking_id}/status` - Обновить статус

### Чат 

- `POST /api/v1/chat/messages` - Отправить сообщение
- `GET /api/v1/chat/bookings/{booking_id}/messages` - История чата
- `GET /api/v1/chat/my-chats` - Все чаты пользователя
- `DELETE /api/v1/chat/messages/{message_id}` - Удалить сообщение

### Волонтёры

- `GET /api/v1/volunteers` - Список волонтёров (с фильтрами)
- `GET /api/v1/volunteers/{volunteer_id}` - Информация о волонтёре
- `POST /api/v1/volunteers/register` - Регистрация как волонтёр
- `PATCH /api/v1/volunteers/{volunteer_id}/availability` - Обновить доступность

## Примеры использования

### 1. Регистрация пользователя

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Петров",
    "phone": "+79991234567",
    "email": "ivan@example.com",
    "role": "relative"
  }'
```

### 2. Вход в систему

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+79991234567",
    "otp": "123456"
  }'
```

Сохраните полученный `access_token` для дальнейших запросов.

### 3. Создание SOS события

```bash
curl -X POST http://localhost:8000/api/v1/sos \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "BRSLT-00001234",
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-02-06T12:00:00Z",
    "lat": 55.751244,
    "lon": 37.618423,
    "accuracy_m": 10,
    "battery_percent": 75,
    "signal_type": "LTE",
    "sos_type": "SHORT_PRESS"
  }'
```

### 4. Отправка сообщения в чат

```bash
curl -X POST http://localhost:8000/api/v1/chat/messages \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": 1,
    "message": "Здравствуйте! Я буду через 10 минут"
  }'
```

### 5. Получение истории чата

```bash
curl -X GET http://localhost:8000/api/v1/chat/bookings/1/messages \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## База данных

### Основные таблицы

- `users` - Пользователи (родственники, операторы, волонтёры)
- `devices` - Устройства (браслеты)
- `med_cards` - Медицинские карты
- `sos_events` - SOS события (с геоданными PostGIS)
- `volunteers` - Карточки волонтёров
- `bookings` - Бронирования визитов
- `chat_messages` - Сообщения чата 
- `notifications_log` - Логи уведомлений

### Подключение к БД

```bash
# Через Docker
docker exec -it pozily_db psql -U pozily_user -d pozily_db

# Локально (если PostgreSQL установлен)
psql -h localhost -U pozily_user -d pozily_db
```

## Роли пользователей

- `relative` - Родственник/опекун (может создавать бронирования, получать SOS)
- `volunteer` - Волонтёр (получает бронирования, общается в чате)
- `operator` - Оператор (управляет системой, видит все события)
- `admin` - Администратор (полный доступ)

## Функция чата

Чат создаётся автоматически при бронировании волонтёра. Участники:
- Клиент (родственник)
- Волонтёр

**Возможности:**
- Отправка текстовых сообщений
- Просмотр истории
- Список всех активных чатов
- Удаление своих сообщений

## Особенности MVP

1. **OTP упрощен** - используется фиксированный код "123456"
2. **Уведомления** - заглушка (записываются в БД, не отправляются)
3. **HMAC подпись** - отложена на post-MVP
4. **Kafka** - не добавлена (по требованию)
5. **Шифрование медкарт** - подготовлено поле, логика упрощена

## Разработка

### Локальный запуск без Docker

```bash
# Установите зависимости
pip install -r requirements.txt

# Настройте переменные окружения
export POSTGRES_HOST=localhost
# ... другие переменные из .env

# Запустите приложение
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Остановка сервисов

```bash
docker-compose down
```

### Очистка всех данных

```bash
docker-compose down -v
```

## Мониторинг

- Логи приложения: `docker-compose logs -f app`
- Логи БД: `docker-compose logs -f db`
- Логи Redis: `docker-compose logs -f redis`

## Следующие шаги (Post-MVP)

1. Реальная отправка SMS/Push уведомлений
2. WebSocket для реального времени чата
3. Шифрование медицинских данных
4. HMAC подпись для устройств
5. Rate limiting
6. Kafka для событий
7. Метрики и мониторинг (Prometheus/Grafana)
8. CI/CD pipeline

## Лицензия

Proprietary - Pozily Project

## Контакты

Для вопросов и предложений обращайтесь к команде разработки.
