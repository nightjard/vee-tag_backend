from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# Base Response
class BaseResponse(BaseModel):
    status: str = "ok"
    code: int = 200
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


# Auth Schemas
class LoginRequest(BaseModel):
    phone: str
    otp: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: Dict[str, Any]


class RefreshRequest(BaseModel):
    refresh_token: str


# User Schemas
class UserBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    role: str


class UserCreate(UserBase):
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Device Schemas
class DeviceRegisterRequest(BaseModel):
    device_id: str
    imei: str
    hardware_version: Optional[str] = None
    firmware_version: Optional[str] = None


class DeviceRegisterResponse(BaseModel):
    device_id: str
    registered: bool


class TelemetryRequest(BaseModel):
    timestamp: datetime
    lat: float
    lon: float
    accuracy_m: int
    battery_percent: int
    signal_type: str
    status: str = "OK"


# SOS Schemas
class SOSCreateRequest(BaseModel):
    device_id: str
    event_id: UUID
    timestamp: datetime
    lat: float
    lon: float
    accuracy_m: int
    battery_percent: int
    signal_type: str
    sos_type: str = "SHORT_PRESS"
    additional: Optional[Dict[str, Any]] = None


class SOSCreateResponse(BaseModel):
    event_id: UUID
    sos_id: int
    status: str
    notified: bool


class SOSDetailResponse(BaseModel):
    sos_id: int
    event_id: UUID
    device_id: str
    user: Dict[str, Any]
    lat: float
    lon: float
    accuracy_m: int
    timestamp: datetime
    status: str
    actions: List[Dict[str, Any]] = []


class SOSAckRequest(BaseModel):
    user_id: int
    action: str = "ack"
    comment: Optional[str] = None


# MedCard Schemas
class MedCardData(BaseModel):
    blood_type: Optional[str] = None
    allergies: List[str] = []
    chronic: List[str] = []
    contacts: List[Dict[str, str]] = []


class MedCardResponse(BaseModel):
    medcard_id: int
    user_id: int
    data: MedCardData


# Volunteer Schemas
class VolunteerResponse(BaseModel):
    id: int
    name: str
    rating: float
    services: List[str]
    next_available: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Booking Schemas
class BookingCreateRequest(BaseModel):
    user_id: int
    volunteer_id: int
    slot: datetime
    address: str
    notes: Optional[str] = None


class BookingCreateResponse(BaseModel):
    booking_id: int
    status: str


class BookingResponse(BaseModel):
    id: int
    user_id: int
    volunteer_id: int
    slot: datetime
    address: str
    notes: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Chat Schemas
class ChatMessageCreate(BaseModel):
    booking_id: int
    message: str


class ChatMessageResponse(BaseModel):
    id: int
    booking_id: int
    sender_id: int
    sender_name: str
    message: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    booking_id: int
    messages: List[ChatMessageResponse]


# Notification Schemas
class NotificationSendRequest(BaseModel):
    sos_id: int
    recipients: List[Dict[str, Any]]
    channels: List[str]
    message: str


class NotificationResponse(BaseModel):
    queued: bool

class VolunteerRegisterRequest(BaseModel):
    services: List[str]
    region: str