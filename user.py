import smtplib
import ssl
from email.message import EmailMessage
from utils.sqlService import get_pool
from dotenv import load_dotenv; 
import os

load_dotenv()  # Load environment variables from .env file
class User:

    def __init__(self, username, email):
        self.username = username
        self.email = email
        self.pool = get_pool()
    
    async def reset_password(self, new_password):
        # Use async context manager for aiosqlite/aiosqlitepool
        pool = get_pool()
        async with pool.connection() as conn:
            await conn.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, self.username))
            await conn.commit()
        
    def send_recovery_email(self):
        """
        Sends a password recovery email to the user using SMTP with SSL.
        Args:
            smtp_server (str): SMTP server address (e.g., 'smtp.gmail.com')
            smtp_port (int): SMTP SSL port (e.g., 465)
            smtp_user (str): SMTP login username/email
            smtp_password (str): SMTP login password

        """
        recovery_code = os.urandom(16).hex()  # Generate a random recovery code
        msg = EmailMessage()
        msg['Subject'] = 'Password Recovery'
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = self.email
        msg.set_content(f"You requested a password reset. Use the following code to reset your password: {recovery_code}")

        context = ssl.create_default_context()
        try:
            load_dotenv()
            smtp_server = os.getenv('SMTP_SERVER')
            smtp_port = os.getenv('SMTP_PORT')
            smtp_user = os.getenv('SMTP_USER')
            smtp_password = os.getenv('SMTP_PASSWORD')
            if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
                raise ValueError("SMTP environment variables are not all set.")
            with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                server.starttls(context=context)
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            print(f"Recovery email sent to {self.email}")
        except Exception as e:
            print(f"Failed to send recovery email: {e}")
        return recovery_code
    def __str__(self):
        return f"User(username='{self.username}', email='{self.email}')"

class Moderator(User):
    def __init__(self, username, email):
        super().__init__(username, email)

    def send_message(self, message):
        print(f"Moderator '{self.username}' sends message: {message}")