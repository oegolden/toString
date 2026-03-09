from os import name
import sqlite3
from utils.sqlService import get_pool

class User:
    def __init__(self, username, email, password):
        self.pool = get_pool()
        with self.pool.connection() as conn:
            cursor = conn.execute("SELECT user_id FROM users WHERE username = ? and password = ?", (username, password))
            row = cursor.fetchone()
            if row:
                self.user_id = row['user_id']
            else:
                cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
                self.user_id = cursor.lastrowid
                conn.commit()
        self.username = username
        self.email = email
        self.password = password
        self.subscribed_boards = self.get_subscribed_boards()

    def __str__(self):
        return f"User(username='{self.username}', email='{self.email}')"

    def send_message(self, msg):
        return msg
    
    def get_subscribed_boards(self):
        with self.pool.connection() as conn:
            cursor = conn.execute("SELECT b.name FROM board_subscriptions bs JOIN messageBoard b ON bs.message_board_name = b.name WHERE bs.user_id = ?", (self.user_id,))
            boards = [row['name'] for row in cursor]
            self.subscribed_boards = boards
        return boards
    
class Moderator(User):
    def __init__(self, username, email, password):
        super().__init__(username, email, password)