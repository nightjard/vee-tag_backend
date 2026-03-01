# app/services/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Optional

class EmailService:
    """Сервис для отправки email через Gmail SMTP"""
    
    def __init__(self):
        # Gmail SMTP settings
        self.smtp_server = os.getenv("SMTP_HOST", "smtp.yandex.ru")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        
        # Получаем credentials из переменных окружения
        self.sender_email = os.getenv("GMAIL_USER")
        self.sender_password = os.getenv("GMAIL_APP_PASSWORD")
        
        # Название приложения
        self.app_name = "Vee-tag"
    
    def send_otp_email(self, to_email: str, otp_code: str, user_name: Optional[str] = None) -> bool:
        """
        Отправка OTP кода на email
        
        Args:
            to_email: Email получателя
            otp_code: OTP код (обычно 6 цифр)
            user_name: Имя пользователя (опционально)
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Создаём сообщение
            message = MIMEMultipart("alternative")
            message["Subject"] = f"{self.app_name} - Код подтверждения"
            message["From"] = self.sender_email
            message["To"] = to_email
            
            # Текстовая версия
            text = f"""
Здравствуйте{f', {user_name}' if user_name else ''}!

Ваш код подтверждения для входа в {self.app_name}:

{otp_code}

Код действителен 10 минут.

Если вы не запрашивали этот код, проигнорируйте это письмо.

---
{self.app_name}
Платформа помощи пожилым людям
            """
            
            # HTML версия (красивая)
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .otp-code {{ background: white; border: 2px dashed #667eea; 
                     padding: 20px; text-align: center; font-size: 32px; 
                     font-weight: bold; letter-spacing: 8px; margin: 20px 0; 
                     border-radius: 8px; color: #667eea; }}
        .info {{ background: #fff3cd; border-left: 4px solid #ffc107; 
                 padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤝 {self.app_name}</h1>
            <p>Код подтверждения для входа</p>
        </div>
        <div class="content">
            <p>Здравствуйте{f', <strong>{user_name}</strong>' if user_name else ''}!</p>
            
            <p>Ваш код подтверждения для входа в систему:</p>
            
            <div class="otp-code">
                {otp_code}
            </div>
            
            <div class="info">
                ⏰ <strong>Код действителен 10 минут</strong>
            </div>
            
            <p>Если вы не запрашивали этот код, проигнорируйте это письмо.</p>
        </div>
        <div class="footer">
            <p>{self.app_name} - Платформа помощи пожилым людям</p>
        </div>
    </div>
</body>
</html>
            """
            
            # Прикрепляем обе версии
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            message.attach(part1)
            message.attach(part2)
            
            # Отправляем через SMTP
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, to_email, message.as_string())
            
            print()
            print(f"✅ OTP email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send OTP email: {e}", self.sender_password, self.sender_email)
            return False


# Singleton instance
_email_service = EmailService()

def send_otp_email(to_email: str, otp_code: str, user_name: Optional[str] = None) -> bool:
    """Helper функция для отправки OTP"""
    return _email_service.send_otp_email(to_email, otp_code, user_name)