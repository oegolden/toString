import pytest
from user import User, Moderator
import sqlite3
from utils.sqlService import get_pool

@pytest.fixture(scope="module")
def setup_db():
	pool = get_pool()
	with pool.connection() as conn:
		conn.execute("DELETE FROM users")
		conn.commit()
	return pool

def test_user_creation(setup_db):
	user = User("testuser", "test@example.com", "password123")
	assert user.username == "testuser"
	assert user.email == "test@example.com"
	assert user.user_id is not None

def test_user_duplicate(setup_db):
	user1 = User("dupuser", "dup@example.com", "pass1")
	user2 = User("dupuser", "dup@example.com", "pass1")
	assert user1.user_id == user2.user_id

def test_user_str(setup_db):
	user = User("struser", "str@example.com", "pass2")
	assert str(user) == "User(username='struser', email='str@example.com')"

def test_moderator_inherits_user(setup_db):
	mod = Moderator("moduser", "mod@example.com", "modpass")
	assert isinstance(mod, User)
	assert mod.username == "moduser"

