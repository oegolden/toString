from os import name
import sqlite3
from utils.sqlService import get_pool

class MessageBoard:
    def __init__(self, moderator, name):
        try:
            self.pool = get_pool()
        except RuntimeError:
             raise RuntimeError("Database pool not initialized. Please call init_pool() before creating a MessageBoard instance.")
        self.moderator = moderator
        self.name = name
        self.messages = {}
        with self.pool.connection() as conn:
            cursor = conn.execute("SELECT message_id, message FROM messageBoard join messages on messageBoard.message_id = messages.message_id WHERE name = ? and moderator = ? AND status = 1", (name, moderator))
            for row in cursor:
                self.messages[row['message_id']] = row['message'] 

    async def add_message(self, message, message_id, user):
        self.messages[message_id] = message
        async with self.pool.connection() as conn:
            await conn.execute("INSERT INTO messages (message_id, message, user, status) VALUES (?, ?, ?,1)", (message_id, message, user))
            await conn.commit()

    async def get_messages(self):
        return self.messages
    
    async def clear_messages(self, user, message_id):
        if user == self.moderator:
            self.messages.pop(message_id, None)
            async with self.pool.connection() as conn:
                await conn.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))
                await conn.commit()
        else:
            user.send_message(f"You do not have permission to clear messages. Only the moderator '{self.moderator}' can clear messages.")