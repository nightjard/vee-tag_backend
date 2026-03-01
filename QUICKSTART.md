# 🚀 Быстрый старт Pozily Backend

## За 5 минут до работающего API

### Шаг 1: Запуск

```bash
# Убедитесь что Docker установлен
docker --version
docker-compose --version

# Запустите всё одной командой
make install

# Или вручную:
docker-compose up --build
```

Подождите пока запустятся сервисы (30-60 секунд).

### Шаг 2: Проверка

Откройте в браузере:
- **API Health**: http://localhost:8000/health
- **Swagger UI**: http://localhost:8000/docs

Должны увидеть интерактивную документацию API.

### Шаг 3: Тестирование чата

```bash
# В новом терминале запустите тест
python3 test_api.py
```

Скрипт автоматически:
1. ✅ Зарегистрирует клиента и волонтёра
2. ✅ Создаст бронирование
3. ✅ Отправит сообщения в чат
4. ✅ Покажет историю переписки

---

## Основные команды

```bash
make up          # Запустить сервисы
make down        # Остановить
make logs        # Смотреть логи
make test        # Запустить тесты
make clean       # Очистить всё
```

---

## Быстрый тест через cURL

### 1. Регистрация пользователя

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тест Тестов",
    "phone": "+79999999999",
    "role": "relative"
  }'
```

### 2. Вход (получение токена)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+79999999999",
    "otp": "123456"
  }'
```

Скопируйте `access_token` из ответа.

### 3. Проверка работы API

```bash
TOKEN="ваш_access_token_здесь"

curl -X GET http://localhost:8000/api/v1/volunteers \
  -H "Authorization: Bearer $TOKEN"
```

---

## Тестовые данные

После первого запуска можно инициализировать тестовые данные:

```bash
make init-data
```

Будут созданы:
- 👥 2 родственника
- 🤝 3 волонтёра
- 👨‍💼 1 оператор
- 📟 2 браслета

**Все OTP коды: 123456**

---

## Структура endpoints

```
/api/v1/
├── auth/              # Аутентификация
│   ├── register
│   ├── login
│   └── refresh
├── devices/           # Устройства
│   ├── register
│   └── {id}/telemetry
├── sos/               # SOS события
│   ├── (POST)
│   ├── {id}
│   └── {id}/ack
├── bookings/          # Бронирования
│   ├── (POST)
│   ├── (GET)
│   └── {id}
├── chat/            # Чат
│   ├── messages
│   ├── bookings/{id}/messages
│   └── my-chats
└── volunteers/        # Волонтёры
    ├── (GET)
    ├── {id}
    └── register
```

---

## Типичный flow

```
1. Регистрация → 2. Вход → 3. Токен
                              ↓
4. Поиск волонтёра ← ← ← ← ← ← ┘
         ↓
5. Создание бронирования
         ↓
6. СОЗДАЁТСЯ ЧАТ 
         ↓
7. Обмен сообщениями
```

---

## Полезные ссылки

- 📚 [Полная документация](README.md)
- 💬 [Документация по чату](CHAT_DOCUMENTATION.md)
- 🔍 [Swagger UI](http://localhost:8000/docs)
- 🏥 [Health Check](http://localhost:8000/health)

---

## Проблемы?

### Порт занят
```bash
# Измените порт в docker-compose.yml
ports:
  - "8001:8000"  # вместо 8000:8000
```

### База не запускается
```bash
# Очистите всё и начните заново
make clean
make install
```

### API не отвечает
```bash
# Проверьте логи
make logs-app
```

---

## Следующие шаги

1. ✅ Изучите [Swagger документацию](http://localhost:8000/docs)
2. ✅ Запустите полный тест: `python3 test_api.py`
3. ✅ Прочитайте [документацию по чату](CHAT_DOCUMENTATION.md)
4. ✅ Попробуйте создать своё первое бронирование

**Готово! 🎉 Система работает!**
