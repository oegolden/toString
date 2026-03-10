"""
Authentication tests for .toString(object).

These tests verify login and registration behavior and confirm that
invalid credentials are rejected.
"""

import pytest
import mock_client


class TestLogin:
    """Authentication: login behavior."""

    def test_valid_login_succeeds(self):
        """Valid username and password should return user info."""
        result = mock_client.login("alice", "pass123")
        assert result["username"] == "alice"
        assert result["role"] == "user"

    def test_valid_login_moderator(self):
        """Moderator login should return moderator role."""
        result = mock_client.login("bob", "pass456")
        assert result["username"] == "bob"
        assert result["role"] == "moderator"

    def test_invalid_password_fails(self):
        """Wrong password should raise Exception."""
        with pytest.raises(Exception, match="Invalid username or password"):
            mock_client.login("alice", "wrongpassword")

    def test_nonexistent_user_fails(self):
        """Nonexistent username should raise Exception."""
        with pytest.raises(Exception, match="Invalid username or password"):
            mock_client.login("nonexistent_user", "anypassword")

    def test_empty_username_fails(self):
        """Empty username should fail (treated as nonexistent)."""
        with pytest.raises(Exception, match="Invalid username or password"):
            mock_client.login("", "pass123")

    def test_login_case_sensitive_username(self):
        """Username matching is case-sensitive; 'Alice' != 'alice'."""
        with pytest.raises(Exception, match="Invalid username or password"):
            mock_client.login("Alice", "pass123")


class TestRegister:
    """Authentication: registration behavior."""

    def test_register_new_user_succeeds(self):
        """New user registration should succeed."""
        result = mock_client.register("newuser", "securepass")
        assert result["username"] == "newuser"
        assert result["role"] == "user"

    def test_register_taken_username_fails(self):
        """Registration with existing username should fail."""
        with pytest.raises(Exception, match="already taken"):
            mock_client.register("alice", "differentpass")

    def test_register_short_password_fails(self):
        """Password shorter than 4 characters should fail."""
        with pytest.raises(Exception, match="at least 4 characters"):
            mock_client.register("shortpassuser", "123")

    def test_register_empty_username_fails(self):
        """Registration with empty username should fail."""
        with pytest.raises(Exception):
            mock_client.register("", "validpass")

    def test_register_empty_password_fails(self):
        """Registration with empty password should fail."""
        with pytest.raises(Exception):
            mock_client.register("userx", "")
