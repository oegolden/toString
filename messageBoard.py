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
            cursor = conn.execute("SELECT name FROM messageBoard WHERE name = ?", (name,))
            if cursor.fetchone() is None:
                conn.execute("INSERT INTO messageBoard (name, private, moderator) VALUES (?, ?, ?)", (name, 0, moderator))
                conn.commit()
        
    async def add_message(self, message, message_id, user):
            self.messages[message_id] = message
            async with self.pool.connection() as conn:
                await conn.execute("INSERT INTO messages (message_id, user_id, message, status) VALUES (?, ?, ?, ?)", (message_id, user.user_id, message, 0))
                await conn.commit()

    async def get_messages(self):
        return self.messages
    
    async def get_messages_by_user(self, user):
        user_messages = {msg_id: msg for msg_id, msg in self.messages.items() if msg['user'] == user}
        return user_messages

    async def clear_messages(self, user, message_id):
        if user == self.moderator:
            self.messages.pop(message_id, None)
            async with self.pool.connection() as conn:
                await conn.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))
                await conn.commit()
        else:
            user.send_message(f"You do not have permission to clear messages. Only the moderator '{self.moderator}' can clear messages.")

    async def edit_message(self, user, message_id, new_message):
        if user == self.moderator:
            if message_id in self.messages:
                self.messages[message_id] = new_message
                async with self.pool.connection() as conn:
                    await conn.execute("UPDATE messages SET message = ? WHERE message_id = ?", (new_message, message_id))
                    await conn.commit()
            else:
                user.send_message(f"Message ID {message_id} does not exist.")
        else:
            user.send_message(f"You do not have permission to edit messages. Only the moderator '{self.moderator}' can edit messages.")
        
    async def subscribe_user(self, user):
        async with self.pool.connection() as conn:
            await conn.execute("INSERT INTO board_subscriptions (user_id, message_board_name) VALUES (?, ?)", (user.user_id, self.name))
            await conn.commit()