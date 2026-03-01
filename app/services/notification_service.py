from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Notification, User
from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# TODO: Kafka integration
# from aiokafka import AIOKafkaProducer
# import json

class NotificationService:
    """
    Сервис для работы с уведомлениями
    
    Поддерживает:
    - Сохранение в БД
    - TODO: Отправка в Kafka для масштабирования
    - TODO: Push уведомления через FCM
    - TODO: Email уведомления
    """
    
    def __init__(self):
        self.kafka_enabled = False  # TODO: Включить когда настроен Kafka
        # self.kafka_producer = None
    
    async def send_notification(
        self,
        db: AsyncSession,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[dict] = None
    ):
        """
        Отправка уведомления пользователю
        
        Args:
            db: Database session
            user_id: ID получателя
            notification_type: Тип уведомления (booking_created, etc.)
            title: Заголовок
            message: Текст сообщения
            data: Дополнительные данные (booking_id, etc.)
        """
        try:
            # 1. Сохраняем в БД
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message,
                data=data or {},
                read=False,
                created_at=datetime.utcnow()
            )
            
            db.add(notification)
            await db.commit()
            await db.refresh(notification)
            
            logger.info(f"✉️ Notification created: {notification_type} for user {user_id}")
            
            # 2. TODO: Отправка в Kafka для обработки
            if self.kafka_enabled:
                await self._send_to_kafka(notification)
            
            # 3. TODO: Push уведомление (FCM)
            # await self._send_push(user_id, title, message)
            
            return notification
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
            # Не падаем если уведомление не отправилось
            return None
    
    async def _send_to_kafka(self, notification: Notification):
        """
        TODO: Отправка события в Kafka
        
        Kafka topics:
        - notifications.created - новое уведомление
        - notifications.read - уведомление прочитано
        - notifications.push - требуется push
        """
        # kafka_message = {
        #     "id": notification.id,
        #     "user_id": notification.user_id,
        #     "type": notification.type,
        #     "title": notification.title,
        #     "message": notification.message,
        #     "data": notification.data,
        #     "timestamp": notification.created_at.isoformat()
        # }
        # 
        # await self.kafka_producer.send(
        #     "notifications.created",
        #     json.dumps(kafka_message).encode('utf-8')
        # )
        pass
    
    async def mark_as_read(self, db: AsyncSession, notification_id: int):
        """Отметить уведомление как прочитанное"""
        from sqlalchemy import select, update
        
        await db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(read=True)
        )
        await db.commit()
    
    async def mark_all_as_read(self, db: AsyncSession, user_id: int):
        """Отметить все уведомления пользователя как прочитанные"""
        from sqlalchemy import update
        
        await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id)
            .values(read=True)
        )
        await db.commit()


# Singleton instance
notification_service = NotificationService()


# Helper functions для удобства

async def notify_booking_created(db: AsyncSession, volunteer_id: int, booking_id: int, address: str):
    """Уведомление волонтёру о новой заявке"""
    await notification_service.send_notification(
        db=db,
        user_id=volunteer_id,
        notification_type="booking_created",
        title="Новая заявка",
        message=f"Вам назначена новая заявка по адресу: {address}",
        data={"booking_id": booking_id}
    )


async def notify_booking_confirmed(db: AsyncSession, user_id: int, booking_id: int, volunteer_name: str):
    """Уведомление родственнику о подтверждении"""
    await notification_service.send_notification(
        db=db,
        user_id=user_id,
        notification_type="booking_confirmed",
        title="Заявка подтверждена",
        message=f"Волонтёр {volunteer_name} подтвердил вашу заявку",
        data={"booking_id": booking_id}
    )


async def notify_booking_completed(db: AsyncSession, user_id: int, booking_id: int):
    """Уведомление родственнику о завершении"""
    await notification_service.send_notification(
        db=db,
        user_id=user_id,
        notification_type="booking_completed",
        title="📝 Заявка выполнена",
        message="Волонтёр завершил работу. Пожалуйста, оцените качество",
        data={"booking_id": booking_id}
    )


async def notify_sos_triggered(db: AsyncSession, user_id: int, lat: float, lon: float):
    """Уведомление об SOS"""
    await notification_service.send_notification(
        db=db,
        user_id=user_id,
        notification_type="sos_triggered",
        title="SOS АКТИВИРОВАН",
        message=f"Зафиксирован сигнал SOS. Координаты: {lat}, {lon}",
        data={"lat": lat, "lon": lon}
    )


async def notify_chat_message(db: AsyncSession, user_id: int, sender_name: str, booking_id: int):
    """Уведомление о новом сообщении в чате"""
    await notification_service.send_notification(
        db=db,
        user_id=user_id,
        notification_type="chat_message",
        title="Новое сообщение",
        message=f"{sender_name} отправил вам сообщение",
        data={"booking_id": booking_id}
    )