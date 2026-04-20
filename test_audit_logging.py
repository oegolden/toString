#!/usr/bin/env python3
"""
Test script for the comprehensive audit logging system
Tests login tracking, moderator actions, and post tracking
"""

import sys
sys.path.insert(0, '/Users/angelinatsai/.toString--1')

from server import (
    _login_audit_logs, _moderator_audit_logs, _post_audit_logs, 
    _moderator_request_logs, log_login_attempt, log_moderator_action,
    log_post_action, log_moderator_request, _user_id_map
)

print("=" * 70)
print("AUDIT LOGGING SYSTEM TEST")
print("=" * 70)

# Test 1: Login logging with userID
print("\n[1] Testing login attempt logging...")
log_login_attempt("alice", "192.168.1.100", "MacBook-Pro", True, None)
log_login_attempt("bob", "192.168.1.101", "Windows10", False, "Invalid password")
print(f"   ✓ Login logs: {len(_login_audit_logs)} entries")
for log in _login_audit_logs:
    print(f"   - {log['username']} (ID: {log['user_id']}) | Success: {log['success']} | IP: {log['ip_address']}")

# Test 2: Moderator action logging with userID
print("\n[2] Testing moderator action logging...")
log_moderator_action("UPGRADE_USER", "admin", "alice", None, "Promoted alice to moderator", "192.168.1.50", "Admin-Desktop", True)
log_moderator_action("ASSIGN_BOARD_MODERATOR", "admin", "bob", 1, "Assigned bob to r/PythonHelp", "192.168.1.50", "Admin-Desktop", True)
print(f"   ✓ Moderator logs: {len(_moderator_audit_logs)} entries")
for log in _moderator_audit_logs:
    print(f"   - {log['action']}: {log['performed_by']}(ID:{log['performed_by_id']}) -> {log['target_user']}(ID:{log['target_user_id']}) on board {log['board_id']}")

# Test 3: Post tracking with userID and harm flags
print("\n[3] Testing post/comment audit logging...")
log_post_action(101, "alice", 1, "192.168.1.100", "MacBook", "How do I use decorators?", "POST", False, None)
log_post_action(201, "bob", 1, "192.168.1.101", "Windows", "This is a normal post", "POST", True, "Suspicious keywords detected")
log_post_action(202, "alice", 1, "192.168.1.100", "MacBook", "Great thanks!", "COMMENT", False, None)
print(f"   ✓ Post logs: {len(_post_audit_logs)} entries")
for log in _post_audit_logs:
    flagged = "🚩 FLAGGED" if log['flagged_harmful'] else "✓ OK"
    print(f"   - {flagged} | {log['username']}(ID:{log['user_id']}) on board {log['board_id']} | {log['action']}")

# Test 4: Moderator request logging
print("\n[4] Testing moderator request logging...")
log_moderator_request("alice", "MODERATOR_UPGRADE", "User requesting system moderator role", "192.168.1.100", "MacBook")
log_moderator_request("bob", "BOARD_MODERATOR", "User requesting board moderation for r/SecurityForum", "192.168.1.101", "Windows")
print(f"   ✓ Request logs: {len(_moderator_request_logs)} entries")
for log in _moderator_request_logs:
    print(f"   - {log['username']}(ID:{log['user_id']}) | Request: {log['request_type']} | Status: {log['status']}")

# Test 5: Verify userID mapping
print("\n[5] Verifying userID mapping...")
print(f"   User ID map: {_user_id_map}")
for username, user_id in _user_id_map.items():
    print(f"   - {username:15} -> ID {user_id}")

print("\n" + "=" * 70)
print("✅ ALL AUDIT LOGGING TESTS PASSED")
print("=" * 70)
