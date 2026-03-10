"""
Messaging tests for .toString(object).

These tests verify that messages and comments are stored and displayed correctly.
"""

import pytest
import mock_client


class TestPostMessage:
    """Messaging: posting messages."""

    def test_message_sends_to_board(self):
        """Message successfully sends to subscribed board."""
        result = mock_client.post_message("alice", 1, "Test message content")
        assert result["board_id"] == 1
        assert result["author"] == "alice"
        assert result["content"] == "Test message content"
        assert "id" in result
        assert "timestamp" in result

    def test_message_appears_in_board(self):
        """Posted message appears when fetching board messages."""
        posted = mock_client.post_message("bob", 1, "New post from bob")
        msgs = mock_client.get_messages(1)
        found = next((m for m in msgs if m["id"] == posted["id"]), None)
        assert found is not None
        assert found["content"] == "New post from bob"

    def test_multiple_users_can_post(self):
        """Multiple users can post to same board."""
        m1 = mock_client.post_message("alice", 1, "Alice says hi")
        m2 = mock_client.post_message("bob", 1, "Bob says hi")
        msgs = mock_client.get_messages(1)
        ids = [m["id"] for m in msgs]
        assert m1["id"] in ids
        assert m2["id"] in ids


class TestComments:
    """Messaging: comments on posts."""

    def test_post_comment_succeeds(self):
        """Comment can be posted on existing message."""
        result = mock_client.post_comment("alice", 102, "Great point!")
        assert result["author"] == "alice"
        assert result["content"] == "Great point!"
        assert "id" in result

    def test_comment_appears_in_message(self):
        """Posted comment appears in message's comments list."""
        comment = mock_client.post_comment("bob", 101, "Nice question")
        msgs = mock_client.get_messages(1)
        msg_101 = next(m for m in msgs if m["id"] == 101)
        assert any(c["id"] == comment["id"] for c in msg_101["comments"])


class TestBoardCreation:
    """Messaging: board creation."""

    def test_create_board_succeeds(self):
        """Board creation succeeds and returns new board."""
        result = mock_client.create_board("alice", "r/NewBoard", "A new board")
        assert result["name"] == "r/NewBoard"
        assert result["description"] == "A new board"
        assert result["creator"] == "alice"

    def test_create_duplicate_board_fails(self):
        """Creating a board with duplicate name fails."""
        mock_client.create_board("alice", "r/DuplicateBoard", "First")
        with pytest.raises(Exception, match="already exists"):
            mock_client.create_board("alice", "r/DuplicateBoard", "Second")
