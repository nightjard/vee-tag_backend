from sqlalchemy import (
    Column, Integer, String, Boolean, SmallInteger, JSON, DateTime,
    ForeignKey, TIMESTAMP, Text, LargeBinary, CheckConstraint, Index, Float
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import uuid
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    phone = Column(String(32), unique=True, nullable=False, index=True)
    email = Column(String(256), nullable=True)
    role = Column(String(32), nullable=False)
    password_hash = Column(String(256), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    qr_token = Column(String(255), unique=True, nullable=True, index=True)
    photo_url = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    __table_args__ = (
        CheckConstraint("role IN ('relative', 'operator', 'volunteer', 'admin')", name='check_user_role'),
    )
    
    # Relationships
    devices = relationship("Device", back_populates="user")
    med_cards = relationship("MedCard", back_populates="user")
    sos_events = relationship("SOSEvent", back_populates="user")
    bookings_as_relative = relationship("Booking", foreign_keys="[Booking.user_id]", back_populates="user")
    bookings_as_volunteer = relationship("Booking", foreign_keys="[Booking.volunteer_id]", back_populates="volunteer")
    chat_messages_sent = relationship("ChatMessage", foreign_keys="[ChatMessage.sender_id]", back_populates="sender")


class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    imei = Column(String(64), nullable=True)
    firmware_version = Column(String(32), nullable=True)
    device_secret = Column(LargeBinary, nullable=True)
    
    # Traccar fields
    last_seen = Column(TIMESTAMP(timezone=True), nullable=True)
    battery_percent = Column(SmallInteger, nullable=True)
    signal_type = Column(String(32), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    course = Column(Float, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="devices")
    sos_events = relationship("SOSEvent", back_populates="device")

class MedCard(Base):
    __tablename__ = "med_cards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    qr_code = Column(String(128), unique=True, nullable=True)
    data_encrypted = Column(LargeBinary, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="med_cards")


class SOSEvent(Base):
    __tablename__ = "sos_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4, unique=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    geom = Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    accuracy_m = Column(Integer, nullable=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    status = Column(String(32), nullable=False, default='new')
    payload = Column(JSONB, nullable=True)
    
    # Relationships
    device = relationship("Device", back_populates="sos_events")
    user = relationship("User", back_populates="sos_events")
    notifications = relationship("NotificationLog", back_populates="sos_event")
    
    __table_args__ = (
        Index('idx_sos_timestamp', 'timestamp'),
        Index('idx_sos_geom', 'geom', postgresql_using='gist'),
    )


class NotificationLog(Base):
    __tablename__ = "notifications_log"
    
    id = Column(Integer, primary_key=True, index=True)
    sos_event_id = Column(Integer, ForeignKey("sos_events.id", ondelete="CASCADE"), nullable=True)
    recipient = Column(String(256), nullable=False)
    channel = Column(String(32), nullable=False)
    delivered = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    sos_event = relationship("SOSEvent", back_populates="notifications")


class Volunteer(Base):
    __tablename__ = "volunteers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, default=0)  # сохраняем как int, можем делить на 10 для UI
    services = Column(JSONB, nullable=True)  # ["visit", "shopping", etc]
    region = Column(String(128), nullable=True)
    available = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user = relationship("User", backref="volunteer_profile")


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    volunteer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    slot = Column(TIMESTAMP(timezone=True), nullable=False)
    address = Column(String(512), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default='confirmed')
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="bookings_as_relative")
    volunteer = relationship("User", foreign_keys=[volunteer_id], back_populates="bookings_as_volunteer")
    chat_messages = relationship("ChatMessage", back_populates="booking")
    
    __table_args__ = (
        Index('idx_booking_slot', 'slot'),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    booking = relationship("Booking", back_populates="chat_messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="chat_messages_sent")
    
    __table_args__ = (
        Index('idx_chat_booking', 'booking_id'),
        Index('idx_chat_timestamp', 'timestamp'),
    )

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    data = Column(JSON, nullable=True) 
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="notifications")

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True)
    volunteer_id = Column(Integer, ForeignKey("volunteers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Кто оставил отзыв
    
    rating = Column(Integer, nullable=False)
    review_text = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    booking = relationship("Booking", backref="review")
    volunteer = relationship("Volunteer", backref="reviews")
    user = relationship("User", backref="reviews_written")