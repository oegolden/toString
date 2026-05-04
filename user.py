import hashlib
import os
import smtplib
import ssl
from email.message import EmailMessage
from utils.sqlService import get_pool
from dotenv import load_dotenv

load_dotenv()


def _hash_password(password: str, salt: bytes = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + '$' + hash_bytes.hex()


def _verify_password(stored: str, provided: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split('$')
        salt = bytes.fromhex(salt_hex)
        provided_hash = hashlib.pbkdf2_hmac('sha256', provided.encode('utf-8'), salt, 100000).hex()
        return provided_hash == hash_hex
    except Exception:
        return False


class User:

    def __init__(self, username, email):
        try:
            self.pool = get_pool()
        except RuntimeError:
            raise RuntimeError("Database pool not initialized. Please call init_pool() before creating a User instance.")
        self.username = username
        self.email = email

    async def register(self, password):
        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (self.username, self.email, _hash_password(password))
            )
            await conn.commit()

    async def login(self, password):
        async with self.pool.connection() as conn:
            cursor = await conn.execute(
                "SELECT password FROM users WHERE username = ?",
                (self.username,)
            )
            row = await cursor.fetchone()
            if row is None:
                return False
            return _verify_password(row[0], password)

    async def reset_password(self, new_password):
        async with self.pool.connection() as conn:
            await conn.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (_hash_password(new_password), self.username)
            )
            await conn.commit()

    def send_recovery_email(self):
        recovery_code = os.urandom(16).hex()
        msg = EmailMessage()
        msg['Subject'] = 'Password Recovery'
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = self.email
        msg.set_content(
            f"You requested a password reset. "
            f"Use the following code to reset your password: {recovery_code}"
        )

        context = ssl.create_default_context()
        try:
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
