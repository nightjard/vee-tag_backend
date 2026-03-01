from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app.models import ChatMessage, Booking, User
from app.schemas import ChatMessageCreate, BaseResponse
from app.dependencies import get_current_user
from typing import Dict, List
from datetime import datetime
import json

router = APIRouter(prefix="/chat", tags=["Chat"])

# Активные WebSocket соединения
active_connections: Dict[int, List[WebSocket]] = {}


class ConnectionManager:
    """Менеджер WebSocket соединений"""
    
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, booking_id: int):
        """Подключение к чату"""
        await websocket.accept()
        if booking_id not in self.active_connections:
            self.active_connections[booking_id] = []
        self.active_connections[booking_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, booking_id: int):
        """Отключение от чата"""
        if booking_id in self.active_connections:
            self.active_connections[booking_id].remove(websocket)
            if not self.active_connections[booking_id]:
                del self.active_connections[booking_id]
    
    async def broadcast(self, message: dict, booking_id: int):
        """Отправка сообщения всем участникам чата"""
        if booking_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[booking_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Удаляем отключенных клиентов
            for conn in disconnected:
                self.disconnect(conn, booking_id)


manager = ConnectionManager()


@router.websocket("/ws/{booking_id}")
async def websocket_chat(
    websocket: WebSocket,
    booking_id: int,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket соединение для чата"""
    await manager.connect(websocket, booking_id)
    
    try:
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_json()
            
            # Сохраняем в БД
            new_message = ChatMessage(
                booking_id=booking_id,
                sender_id=data["sender_id"],
                message=data["message"],
                timestamp=datetime.utcnow()
            )
            
            db.add(new_message)
            await db.commit()
            await db.refresh(new_message)
            
            # Получаем имя отправителя
            user_result = await db.execute(
                select(User).where(User.id == new_message.sender_id)
            )
            user = user_result.scalar_one_or_none()
            
            # Отправляем всем участникам
            message_data = {
                "id": new_message.id,
                "booking_id": new_message.booking_id,
                "sender_id": new_message.sender_id,
                "sender_name": user.name if user else "Unknown",
                "message": new_message.message,
                "timestamp": new_message.timestamp.isoformat()
            }
            
            await manager.broadcast(message_data, booking_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, booking_id)


@router.get("/bookings/{booking_id}/messages", response_model=BaseResponse)
async def get_chat_messages(
    booking_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение истории сообщений чата"""
    # Проверяем доступ к чату
    booking_result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = booking_result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Получаем сообщения
    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.booking_id == booking_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(limit)
    )
    messages = messages_result.scalars().all()
    
    # Формируем ответ
    messages_data = []
    for msg in messages:
        user_result = await db.execute(
            select(User).where(User.id == msg.sender_id)
        )
        user = user_result.scalar_one_or_none()
        
        messages_data.append({
            "id": msg.id,
            "booking_id": msg.booking_id,
            "sender_id": msg.sender_id,
            "sender_name": user.name if user else "Unknown",
            "message": msg.message,
            "timestamp": msg.timestamp.isoformat()
        })
    
    return BaseResponse(
        status="ok",
        code=200,
        data={
            "booking_id": booking_id,
            "messages": list(reversed(messages_data))  # Сортируем по возрастанию
        }
    )


@router.post("/messages", response_model=BaseResponse)
async def send_message(
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Отправка сообщения (REST API fallback)"""
    # Проверяем доступ к бронированию
    booking_result = await db.execute(
        select(Booking).where(Booking.id == message_data.booking_id)
    )
    booking = booking_result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Создаем сообщение
    new_message = ChatMessage(
        booking_id=message_data.booking_id,
        sender_id=current_user.id,
        message=message_data.message,
        timestamp=datetime.utcnow()
    )
    
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    
    # Уведомляем через WebSocket если есть подключения
    message_dict = {
        "id": new_message.id,
        "booking_id": new_message.booking_id,
        "sender_id": new_message.sender_id,
        "sender_name": current_user.name,
        "message": new_message.message,
        "timestamp": new_message.timestamp.isoformat()
    }
    
    await manager.broadcast(message_dict, message_data.booking_id)
    
    return BaseResponse(
        status="ok",
        code=201,
        data=message_dict
    )