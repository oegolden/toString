"""
Authorization tests for .toString(object).

These tests verify that users can only edit/delete their own messages,
cannot post to unsubscribed boards, and that moderators have appropriate permissions.
"""

import pytest
import mock_client


class TestEditAuthorization:
    """Authorization: edit message permissions."""

    def test_user_can_edit_own_message(self):
        """User can edit their own message."""
        result = mock_client.edit_message("alice", 101, "Updated content")
        assert result is True
        msgs = mock_client.get_messages(1)
        edited = next(m for m in msgs if m["id"] == 101)
        assert "Updated content" in edited["content"]

    def test_user_cannot_edit_another_users_message(self):
        """User cannot edit another user's message."""
        with pytest.raises(Exception, match="only edit your own"):
            mock_client.edit_message("alice", 102, "Hacked content")

    def test_moderator_cannot_edit_others_message(self):
        """Moderator cannot edit another user's message (edit is author-only)."""
        with pytest.raises(Exception, match="only edit your own"):
            mock_client.edit_message("bob", 101, "Moderator override")

    def test_edit_nonexistent_message_fails(self):
        """Editing a nonexistent message raises Exception."""
        with pytest.raises(Exception, match="Message not found"):
            mock_client.edit_message("alice", 9999, "ghost edit")


class TestDeleteAuthorization:
    """Authorization: delete message permissions."""

    def test_user_can_delete_own_message(self):
        """User can delete their own message."""
        result = mock_client.delete_message("alice", 101, "user")
        assert result is True
        msgs = mock_client.get_messages(1)
        assert not any(m["id"] == 101 for m in msgs)

    def test_user_cannot_delete_another_users_message(self):
        """Regular user cannot delete another user's message."""
        with pytest.raises(Exception, match="only delete your own"):
            mock_client.delete_message("alice", 102, "user")

    def test_moderator_can_delete_any_message(self):
        """Moderator can delete messages (including others')."""
        result = mock_client.delete_message("bob", 101, "moderator")
        assert result is True

    def test_delete_nonexistent_message_fails(self):
        """Deleting a nonexistent message raises Exception."""
        with pytest.raises(Exception, match="Message not found"):
            mock_client.delete_message("alice", 9999, "user")


class TestBoardAccessAuthorization:
    """Authorization: board subscription and access."""

    def test_user_cannot_post_to_unsubscribed_board(self):
        """User must be subscribed to post on a board."""
        with pytest.raises(Exception, match="must be subscribed"):
            mock_client.post_message("alice", 2, "Unauthorized post")

    def test_user_can_post_to_subscribed_board(self):
        """User can post when subscribed."""
        result = mock_client.post_message("alice", 1, "Hello from alice")
        assert result["author"] == "alice"
        assert result["content"] == "Hello from alice"

    def test_get_messages_returns_for_any_board(self):
        """get_messages returns messages (mock_client allows it).
        Note: Real server should enforce subscription check for GET_MESSAGES."""
        msgs = mock_client.get_messages(1)
        assert isinstance(msgs, list)
        assert len(msgs) >= 1

    @pytest.mark.skip(reason="Waiting for server-side subscription enforcement on GET_MESSAGES")
    def test_user_cannot_read_unsubscribed_board_messages(self):
        """Users should not read boards they are not subscribed to (confidentiality).
        Placeholder for integration test when server enforces subscription check."""
        pass


class TestSubscriptionAuthorization:
    """Authorization: subscription and join behavior."""

    def test_subscribe_user_to_board(self):
        """User can subscribe to a board."""
        result = mock_client.subscribe_board("alice", 2)
        assert result is True

    def test_subscribed_user_can_post_after_joining(self):
        """After subscribing, user can post to the board."""
        mock_client.subscribe_board("alice", 2)
        msg = mock_client.post_message("alice", 2, "Now I can post here")
        assert msg["board_id"] == 2
        assert msg["content"] == "Now I can post here"
