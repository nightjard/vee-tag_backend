# 💬 Документация по чату волонтёр-клиент

## Обзор

Чат между волонтёром и клиентом создаётся автоматически при бронировании визита. Это простая текстовая система обмена сообщениями для координации встречи.

## Архитектура

### Модель данных

Таблица `chat_messages`:
```sql
- id: INTEGER (primary key)
- booking_id: INTEGER (FK -> bookings)
- sender_id: INTEGER (FK -> users)
- message: TEXT
- timestamp: TIMESTAMP
```

### Связи

- Каждое сообщение привязано к **бронированию** (booking)
- У каждого бронирования **два участника**: клиент и волонтёр
- Только участники бронирования могут читать и писать в чат

## API Endpoints

### 1. Отправка сообщения

**POST** `/api/v1/chat/messages`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "booking_id": 1,
  "message": "Здравствуйте! Я буду через 10 минут"
}
```

**Response:**
```json
{
  "status": "ok",
  "code": 201,
  "data": {
    "id": 123,
    "booking_id": 1,
    "sender_id": 42,
    "sender_name": "Александр Петров",
    "message": "Здравствуйте! Я буду через 10 минут",
    "timestamp": "2026-02-06T14:30:00Z"
  }
}
```

**Права доступа:**
- Только участники бронирования (user_id или volunteer_id)

---

### 2. Получение истории чата

**GET** `/api/v1/chat/bookings/{booking_id}/messages?limit=100`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "status": "ok",
  "code": 200,
  "data": {
    "booking_id": 1,
    "messages": [
      {
        "id": 1,
        "booking_id": 1,
        "sender_id": 42,
        "sender_name": "Мария Иванова",
        "message": "Добрый день! Спасибо что согласились помочь",
        "timestamp": "2026-02-06T14:00:00Z"
      },
      {
        "id": 2,
        "booking_id": 1,
        "sender_id": 43,
        "sender_name": "Александр Петров",
        "message": "Здравствуйте! Конечно, помогу с удовольствием",
        "timestamp": "2026-02-06T14:05:00Z"
      }
    ]
  }
}
```

**Параметры:**
- `limit` (optional): максимальное количество сообщений (по умолчанию 100)

**Права доступа:**
- Участники бронирования
- Операторы и администраторы

---

### 3. Список всех чатов пользователя

**GET** `/api/v1/chat/my-chats`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "status": "ok",
  "code": 200,
  "data": [
    {
      "booking_id": 1,
      "other_user": {
        "id": 43,
        "name": "Александр Петров",
        "role": "volunteer"
      },
      "slot": "2026-02-07T14:00:00Z",
      "last_message": {
        "message": "Хорошо, до встречи!",
        "timestamp": "2026-02-06T15:30:00Z"
      },
      "unread_count": 2,
      "booking_status": "confirmed"
    },
    {
      "booking_id": 5,
      "other_user": {
        "id": 45,
        "name": "Ольга Сидорова",
        "role": "volunteer"
      },
      "slot": "2026-02-10T10:00:00Z",
      "last_message": null,
      "unread_count": 0,
      "booking_status": "confirmed"
    }
  ]
}
```

**Описание полей:**
- `other_user`: собеседник (волонтёр для клиента, клиент для волонтёра)
- `unread_count`: количество непрочитанных сообщений (от собеседника)
- `booking_status`: статус бронирования

---

### 4. Удаление сообщения

**DELETE** `/api/v1/chat/messages/{message_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "status": "ok",
  "code": 200,
  "data": {
    "deleted": true
  }
}
```

**Права доступа:**
- Автор сообщения
- Операторы и администраторы

---

## Примеры использования

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "your_access_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Отправка сообщения
data = {
    "booking_id": 1,
    "message": "Привет! Как дела?"
}
response = requests.post(f"{BASE_URL}/chat/messages", json=data, headers=headers)
print(response.json())

# Получение истории
response = requests.get(f"{BASE_URL}/chat/bookings/1/messages", headers=headers)
print(response.json())

# Все чаты
response = requests.get(f"{BASE_URL}/chat/my-chats", headers=headers)
print(response.json())
```

### JavaScript (fetch)

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';
const TOKEN = 'your_access_token_here';

const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json'
};

// Отправка сообщения
const sendMessage = async () => {
  const response = await fetch(`${BASE_URL}/chat/messages`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      booking_id: 1,
      message: 'Привет! Как дела?'
    })
  });
  const data = await response.json();
  console.log(data);
};

// Получение истории
const getHistory = async (bookingId) => {
  const response = await fetch(
    `${BASE_URL}/chat/bookings/${bookingId}/messages`,
    { headers }
  );
  const data = await response.json();
  console.log(data);
};

// Все чаты
const getMyChats = async () => {
  const response = await fetch(`${BASE_URL}/chat/my-chats`, { headers });
  const data = await response.json();
  console.log(data);
};
```

### cURL

```bash
# Отправка сообщения
curl -X POST http://localhost:8000/api/v1/chat/messages \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": 1,
    "message": "Здравствуйте!"
  }'

# История чата
curl -X GET http://localhost:8000/api/v1/chat/bookings/1/messages \
  -H "Authorization: Bearer YOUR_TOKEN"

# Все чаты
curl -X GET http://localhost:8000/api/v1/chat/my-chats \
  -H "Authorization: Bearer YOUR_TOKEN"

# Удаление сообщения
curl -X DELETE http://localhost:8000/api/v1/chat/messages/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Типичные сценарии использования

### Сценарий 1: Создание бронирования и начало чата

1. Клиент создаёт бронирование волонтёра
2. Система автоматически создаёт связь между клиентом и волонтёром
3. Клиент отправляет первое сообщение для уточнения деталей
4. Волонтёр получает уведомление и отвечает
5. Они обмениваются деталями встречи

### Сценарий 2: Координация в день визита

1. Волонтёр в день визита пишет: "Выезжаю к вам"
2. Клиент получает уведомление
3. Волонтёр: "Буду через 15 минут"
4. Клиент: "Хорошо, жду у подъезда"
5. После встречи волонтёр может написать резюме визита

### Сценарий 3: Просмотр всех активных чатов

1. Волонтёр открывает список своих чатов
2. Видит все активные бронирования
3. Может быстро перейти к нужному чату
4. Видит количество непрочитанных сообщений

---

## Безопасность

### Проверки доступа

1. **Аутентификация**: Все endpoints требуют JWT токен
2. **Авторизация**: Доступ только участникам бронирования
3. **Изоляция**: Нельзя читать чужие чаты
4. **Удаление**: Только свои сообщения (или оператор)

### Валидация

- Проверка существования бронирования
- Проверка принадлежности к бронированию
- Валидация формата сообщений
- Защита от SQL-инъекций (SQLAlchemy ORM)

---

## Расширения (Post-MVP)

### Возможные улучшения:

1. **WebSocket для реального времени**
   - Мгновенная доставка сообщений
   - Индикатор "печатает..."
   - Статусы "прочитано"

2. **Вложения**
   - Отправка фото
   - Голосовые сообщения
   - Документы

3. **Уведомления**
   - Push при новом сообщении
   - Email дайджесты
   - SMS для критичных сообщений

4. **Форматирование**
   - Markdown поддержка
   - Эмодзи
   - Упоминания (@mention)

5. **Расширенные функции**
   - Редактирование сообщений
   - Реакции на сообщения
   - Пересылка сообщений
   - Поиск по истории

6. **Групповые чаты**
   - Чат с несколькими волонтёрами
   - Чат с оператором
   - Семейный чат

---

## Мониторинг и метрики

### Полезные метрики:

- Количество отправленных сообщений
- Среднее время ответа волонтёра
- Активность чатов
- Популярные время отправки
- Длина переписки

### Логирование:

Все действия логируются:
- Отправка сообщения
- Чтение истории
- Удаление сообщения
- Ошибки доступа

---

## Troubleshooting

### Проблема: "Booking not found"
**Решение**: Убедитесь что бронирование существует и ID корректен

### Проблема: "Access denied" / 403
**Решение**: Проверьте что пользователь является участником бронирования

### Проблема: "Invalid token" / 401
**Решение**: Обновите JWT токен через `/auth/refresh`

### Проблема: Сообщения не появляются
**Решение**: 
1. Проверьте booking_id
2. Обновите страницу/запрос
3. Проверьте логи сервера

---

## Контакты и поддержка

При возникновении вопросов:
1. Проверьте документацию API: http://localhost:8000/docs
2. Изучите примеры в `test_api.py`
3. Проверьте логи: `docker-compose logs -f app`

**Разработчики**: Pozily Team  
**Версия**: 1.0.0 (MVP)  
**Дата**: 2026-02-06
