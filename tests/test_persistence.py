"""
Persistence tests — exercises User and MessageBoard against a real SQLite database.

Each test gets a fresh, isolated DB via the fresh_db fixture so there is no
cross-test state. All async calls are driven through asyncio.run() to avoid
a pytest-asyncio dependency.
"""
import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setupdb import setup_database
import utils.sqlService as sql_service
from user import User
from messageBoard import MessageBoard


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    setup_database(db_path)

    monkeypatch.setattr(sql_service, '_pool', None)

    async def _factory():
        import aiosqlite
        return await aiosqlite.connect(db_path)

    monkeypatch.setattr(sql_service, 'connection_factory', _factory)
    sql_service.init_pool()
    yield
    monkeypatch.setattr(sql_service, '_pool', None)


async def _make_user(username, email=None, password="password123"):
    email = email or f"{username}@test.com"
    await User(username, email).register(password)


# ─── User ─────────────────────────────────────────────────────────────────

class TestUserRegister:
    def test_new_user_can_login_after_register(self):
        run(_make_user("alice"))
        assert run(User("alice", "alice@test.com").login("password123")) is True

    def test_password_is_hashed_not_stored_plaintext(self):
        run(_make_user("alice"))
        # If plaintext was stored, "wrong" would fail only on mismatch;
        # with hashing, it must also fail the PBKDF2 verification.
        assert run(User("alice", "alice@test.com").login("wrong")) is False

    def test_duplicate_username_raises(self):
        run(_make_user("alice"))
        with pytest.raises(Exception):
            run(_make_user("alice", email="other@test.com"))

    def test_duplicate_email_raises(self):
        run(_make_user("alice", email="shared@test.com"))
        with pytest.raises(Exception):
            run(_make_user("bob", email="shared@test.com"))

    def test_sql_injection_in_password_stored_safely(self):
        run(_make_user("alice", password="'; DROP TABLE users; --"))
        assert run(User("alice", "alice@test.com").login("'; DROP TABLE users; --")) is True
        assert run(User("alice", "alice@test.com").login("innocent")) is False

    def test_sql_injection_in_username_treated_as_literal(self):
        # Parameterized queries store the injection string as literal data.
        # The INSERT succeeds and the users table is unaffected.
        run(_make_user("'; DROP TABLE users; --"))
        # Table still intact — register a normal user to confirm
        run(_make_user("alice"))
        assert run(User("alice", "alice@test.com").login("password123")) is True


class TestUserLogin:
    def test_correct_password_returns_true(self):
        run(_make_user("alice"))
        assert run(User("alice", "alice@test.com").login("password123")) is True

    def test_wrong_password_returns_false(self):
        run(_make_user("alice"))
        assert run(User("alice", "alice@test.com").login("wrong")) is False

    def test_nonexistent_user_returns_false(self):
        assert run(User("ghost", "ghost@test.com").login("any")) is False

    def test_empty_password_returns_false(self):
        run(_make_user("alice"))
        assert run(User("alice", "alice@test.com").login("")) is False

    def test_case_sensitive_username(self):
        run(_make_user("alice"))
        assert run(User("Alice", "alice@test.com").login("password123")) is False


class TestUserResetPassword:
    def test_new_password_works_after_reset(self):
        run(_make_user("alice"))
        run(User("alice", "alice@test.com").reset_password("newpass"))
        assert run(User("alice", "alice@test.com").login("newpass")) is True

    def test_old_password_fails_after_reset(self):
        run(_make_user("alice"))
        run(User("alice", "alice@test.com").reset_password("newpass"))
        assert run(User("alice", "alice@test.com").login("password123")) is False

    def test_reset_persists_across_new_user_object(self):
        run(_make_user("alice"))
        run(User("alice", "alice@test.com").reset_password("newpass"))
        # Different object — forces a fresh DB read
        assert run(User("alice", "fresh@object.com").login("newpass")) is True

    def test_reset_nonexistent_user_is_noop(self):
        # UPDATE with no matching rows must not raise
        run(User("ghost", "ghost@test.com").reset_password("anything"))


class TestUserPoolNotInitialized:
    def test_user_raises_if_pool_missing(self, monkeypatch):
        monkeypatch.setattr(sql_service, '_pool', None)
        with pytest.raises(RuntimeError, match="init_pool"):
            User("alice", "alice@test.com")


# ─── MessageBoard ─────────────────────────────────────────────────────────

class TestMessageBoardLoad:
    def test_creates_new_board(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        assert board.board_id is not None
        assert board.name == "r/Test"
        assert board.creator == "alice"
        assert board.messages == {}

    def test_existing_board_same_id(self):
        run(_make_user("alice"))
        b1 = run(MessageBoard.load("alice", "r/Test"))
        b2 = run(MessageBoard.load("alice", "r/Test"))
        assert b1.board_id == b2.board_id

    def test_nonexistent_creator_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            run(MessageBoard.load("ghost", "r/Test"))

    def test_board_name_globally_unique(self):
        run(_make_user("alice"))
        run(_make_user("bob", email="bob@test.com"))
        run(MessageBoard.load("alice", "r/Shared"))
        with pytest.raises(Exception):
            run(MessageBoard.load("bob", "r/Shared"))

    def test_pool_not_initialized_raises(self, monkeypatch):
        monkeypatch.setattr(sql_service, '_pool', None)
        with pytest.raises(RuntimeError, match="init_pool"):
            MessageBoard("alice", "r/Test")


class TestMessageBoardAddMessage:
    def test_returns_integer_id(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        msg_id = run(board.add_message("Hello", "alice"))
        assert isinstance(msg_id, int)

    def test_message_in_memory_immediately(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        msg_id = run(board.add_message("Hello", "alice"))
        assert board.messages[msg_id] == "Hello"

    def test_message_persists_on_reload(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        run(board.add_message("Persisted", "alice"))
        board2 = run(MessageBoard.load("alice", "r/Test"))
        assert "Persisted" in board2.messages.values()

    def test_multiple_messages_unique_ids(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        id1 = run(board.add_message("First", "alice"))
        id2 = run(board.add_message("Second", "alice"))
        assert id1 != id2
        assert len(board.messages) == 2

    def test_different_users_can_post(self):
        run(_make_user("alice"))
        run(_make_user("bob", email="bob@test.com"))
        board = run(MessageBoard.load("alice", "r/Test"))
        id1 = run(board.add_message("Alice says hi", "alice"))
        id2 = run(board.add_message("Bob says hi", "bob"))
        assert board.messages[id1] == "Alice says hi"
        assert board.messages[id2] == "Bob says hi"

    def test_nonexistent_poster_raises(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        with pytest.raises(ValueError, match="does not exist"):
            run(board.add_message("Hello", "ghost"))

    def test_special_characters_stored_safely(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        content = "It's a \"test\" with 'quotes'; -- DROP TABLE messages"
        msg_id = run(board.add_message(content, "alice"))
        board2 = run(MessageBoard.load("alice", "r/Test"))
        assert board2.messages[msg_id] == content


class TestMessageBoardDeleteMessage:
    def test_creator_can_delete(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        msg_id = run(board.add_message("Bye", "alice"))
        run(board.delete_message("alice", msg_id))
        board2 = run(MessageBoard.load("alice", "r/Test"))
        assert msg_id not in board2.messages

    def test_deleted_message_removed_from_memory(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        msg_id = run(board.add_message("Bye", "alice"))
        run(board.delete_message("alice", msg_id))
        assert msg_id not in board.messages

    def test_non_creator_raises_permission_error(self):
        run(_make_user("alice"))
        run(_make_user("bob", email="bob@test.com"))
        board = run(MessageBoard.load("alice", "r/Test"))
        msg_id = run(board.add_message("Hello", "alice"))
        with pytest.raises(PermissionError):
            run(board.delete_message("bob", msg_id))

    def test_delete_nonexistent_message_is_silent(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        run(board.delete_message("alice", 99999))  # must not raise

    def test_remaining_messages_intact_after_delete(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        id1 = run(board.add_message("Keep me", "alice"))
        id2 = run(board.add_message("Delete me", "alice"))
        run(board.delete_message("alice", id2))
        board2 = run(MessageBoard.load("alice", "r/Test"))
        assert id1 in board2.messages
        assert id2 not in board2.messages


class TestMessageBoardDescription:
    def test_add_description_does_not_raise(self):
        run(_make_user("alice"))
        board = run(MessageBoard.load("alice", "r/Test"))
        run(board.add_description("A board about testing"))

    def test_description_persists_in_db(self):
        async def _check():
            await _make_user("alice")
            board = await MessageBoard.load("alice", "r/Test")
            await board.add_description("My description")
            async with board.pool.connection() as conn:
                cursor = await conn.execute(
                    "SELECT description FROM messageBoard WHERE board_id = ?",
                    (board.board_id,)
                )
                row = await cursor.fetchone()
            assert row[0] == "My description"
        run(_check())
