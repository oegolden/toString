import pytest
import asyncio
from messageBoard import MessageBoard
from user import Moderator
from utils.sqlService import get_pool

@pytest.fixture(scope="module")
def setup_db():
	pool = get_pool()
	with pool.connection() as conn:
		conn.execute("DELETE FROM messageBoard")
		conn.execute("DELETE FROM messages")
		conn.commit()
	return pool

@pytest.mark.asyncio
async def test_messageboard_creation(setup_db):
	mod = Moderator("mod1", "mod1@example.com", "modpass")
	board = MessageBoard(mod.username, "Board1")
	assert board.name == "Board1"
	assert board.moderator == mod.username

@pytest.mark.asyncio
async def test_add_and_get_message(setup_db):
	mod = Moderator("mod2", "mod2@example.com", "modpass")
	board = MessageBoard(mod.username, "Board2")
	await board.add_message("Test Message", 1, mod.username)
	messages = await board.get_messages()
	assert 1 in messages
	assert messages[1] == "Test Message"

@pytest.mark.asyncio
async def test_clear_message_by_moderator(setup_db):
	mod = Moderator("mod3", "mod3@example.com", "modpass")
	board = MessageBoard(mod.username, "Board3")
	await board.add_message("Clear Me", 2, mod.username)
	await board.clear_messages(mod.username, 2)
	messages = await board.get_messages()
	assert 2 not in messages

@pytest.mark.asyncio
async def test_clear_message_by_non_moderator(setup_db, capsys):
	mod = Moderator("mod4", "mod4@example.com", "modpass")
	board = MessageBoard(mod.username, "Board4")
	await board.add_message("Should Not Clear", 3, mod.username)
	class DummyUser:
		def send_message(self, msg):
			print(msg)
		username = "notmod"
	await board.clear_messages(DummyUser(), 3)
	captured = capsys.readouterr()
	assert "You do not have permission to clear messages" in captured.out
