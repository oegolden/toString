from utils.sqlService import get_pool

class MessageBoard:
    def __init__(self, creator, name):
        try:
            self.pool = get_pool()
        except RuntimeError:
            raise RuntimeError("Database pool not initialized. Please call init_pool() before creating a MessageBoard instance.")
        self.creator = creator  # username string
        self.name = name
        self.board_id = None
        self.messages = {}  # message_id -> message text

    @classmethod
    async def load(cls, creator, name):
        """Load an existing board or create it, returning an initialized MessageBoard."""
        board = cls(creator, name)
        async with board.pool.connection() as conn:
            # Validate creator exists before any INSERT
            cursor = await conn.execute(
                "SELECT user_id FROM users WHERE username = ?", (creator,)
            )
            if await cursor.fetchone() is None:
                raise ValueError(f"User '{creator}' does not exist")

            cursor = await conn.execute(
                "SELECT mb.board_id FROM messageBoard mb "
                "JOIN users u ON mb.creator_id = u.user_id "
                "WHERE mb.name = ? AND u.username = ?",
                (name, creator)
            )
            row = await cursor.fetchone()
            if row is None:
                cursor = await conn.execute(
                    "INSERT INTO messageBoard (name, creator_id) "
                    "VALUES (?, (SELECT user_id FROM users WHERE username = ?))",
                    (name, creator)
                )
                await conn.commit()
                board.board_id = cursor.lastrowid
            else:
                board.board_id = row[0]
                cursor = await conn.execute(
                    "SELECT message_id, message FROM messages WHERE board_id = ?",
                    (board.board_id,)
                )
                async for msg_row in cursor:
                    board.messages[msg_row[0]] = msg_row[1]
        return board

    async def add_message(self, message, user):
        """Insert a message and return its generated message_id."""
        async with self.pool.connection() as conn:
            cursor = await conn.execute(
                "SELECT user_id FROM users WHERE username = ?", (user,)
            )
            if await cursor.fetchone() is None:
                raise ValueError(f"User '{user}' does not exist")

            cursor = await conn.execute(
                "INSERT INTO messages (user_id, board_id, message) "
                "VALUES ((SELECT user_id FROM users WHERE username = ?), ?, ?)",
                (user, self.board_id, message)
            )
            await conn.commit()
            message_id = cursor.lastrowid
        self.messages[message_id] = message
        return message_id

    async def add_description(self, description):
        async with self.pool.connection() as conn:
            await conn.execute(
                "UPDATE messageBoard SET description = ? WHERE board_id = ?",
                (description, self.board_id)
            )
            await conn.commit()

    async def get_messages(self):
        return self.messages

    async def delete_message(self, user, message_id):
        if user != self.creator:
            raise PermissionError(
                f"You do not have permission to delete messages. "
                f"Only the creator '{self.creator}' can delete messages."
            )
        self.messages.pop(message_id, None)
        async with self.pool.connection() as conn:
            await conn.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))
            await conn.commit()
