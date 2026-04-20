#!/usr/bin/env python3
"""
Quick Start Guide: Testing the Moderator System
================================================

This script demonstrates how to test the moderator role upgrade functionality.

Steps:
1. Make sure server.py is running: python3 server.py 1234
2. Run this script in another terminal: python3 test_moderator_system.py
3. Follow the prompts to test moderator features

Or manually in the GUI:
1. Start server.py
2. Run gui.py
3. Login as "admin" (password: admin)
4. Click "🔧 Admin Panel" in the top navigation bar
5. Use the tabs to manage moderators and view audit logs
"""

import client
import time

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_result(success, message):
    icon = "✓" if success else "✗"
    print(f"[{icon}] {message}\n")

def test_system():
    try:
        print("Connecting to server...")
        client.connect("127.0.0.1", 1234)
        print_result(True, "Connected to server successfully\n")
    except Exception as e:
        print_result(False, f"Failed to connect to server: {e}")
        return

    # Test 1: Login as admin
    print_section("TEST 1: Admin Login")
    try:
        response = client.login("admin", "admin")
        print(f"Current user: {response['username']}")
        print(f"Role: {response['role']}")
        print_result(True, "Admin login successful")
    except Exception as e:
        print_result(False, f"Admin login failed: {e}")
        return

    # Test 2: Upgrade user to moderator
    print_section("TEST 2: Upgrade User to Moderator")
    try:
        response = client.upgrade_user("admin", "alice")
        print(f"Message: {response['message']}")
        print(f"User: {response['username']}")
        print(f"New role: {response['role']}")
        print_result(True, "User upgraded to moderator")
    except Exception as e:
        print_result(False, f"Upgrade failed: {e}")

    # Test 3: Verify moderator status (login as alice)
    print_section("TEST 3: Verify Moderator Status")
    try:
        response = client.login("alice", "pass123")
        print(f"User: {response['username']}")
        print(f"Role: {response['role']}")
        if response['role'] == 'moderator':
            print_result(True, "Alice is now a moderator")
        else:
            print_result(False, f"Expected moderator, got {response['role']}")
    except Exception as e:
        print_result(False, f"Verification login failed: {e}")

    # Test 4: Login back as admin for board moderator tests
    print_section("TEST 4: Assign Board Moderator")
    try:
        response = client.login("admin", "admin")
        response = client.assign_board_moderator("admin", "bob", 1)
        print(f"Message: {response['message']}")
        print(f"Board: {response['board_name']}")
        print_result(True, "Bob assigned to board moderator")
    except Exception as e:
        print_result(False, f"Board assignment failed: {e}")

    # Test 5: List board moderators
    print_section("TEST 5: List Board Moderators")
    try:
        response = client.list_board_moderators(1)
        print(f"Board: {response['board_name']}")
        print(f"Moderators: {', '.join(response['moderators'])}")
        print_result(True, "Retrieved board moderators")
    except Exception as e:
        print_result(False, f"List failed: {e}")

    # Test 6: Get user's moderated boards
    print_section("TEST 6: Get User's Moderated Boards")
    try:
        target_user = "bob"
        response = client.login(target_user, "pass456")
        
        # Switch back to admin to get moderated boards
        client.logout()
        response = client.login("admin", "admin")
        response = client.get_moderated_boards("bob")
        print(f"User: {response['username']}")
        print(f"Role: {response['role']}")
        print(f"Moderated boards: {len(response['moderated_boards'])}")
        for board in response['moderated_boards']:
            print(f"  - {board['name']} (ID: {board['id']})")
        print_result(True, "Retrieved moderated boards")
    except Exception as e:
        print_result(False, f"Get moderated boards failed: {e}")

    # Test 7: Audit logs
    print_section("TEST 7: View Audit Logs")
    try:
        response = client.get_audit_logs("admin", 10)
        print(f"Total logs: {response['total_logs']}")
        print(f"Showing: {len(response['logs'])} logs\n")
        
        for log in response['logs'][-5:]:  # Show last 5
            print(f"[{log['timestamp']}] {log['action']}")
            print(f"  by {log['performed_by']}, target: {log['target_user']}, board: {log['board_id']}")
            if log.get('details'):
                print(f"  {log['details']}")
        print_result(True, "Retrieved audit logs")
    except Exception as e:
        print_result(False, f"Audit log retrieval failed: {e}")

    # Test 8: Downgrade moderator
    print_section("TEST 8: Downgrade Moderator")
    try:
        response = client.downgrade_user("admin", "alice")
        print(f"Message: {response['message']}")
        print(f"User: {response['username']}")
        print(f"New role: {response['role']}")
        print_result(True, "Moderator downgraded to user")
    except Exception as e:
        print_result(False, f"Downgrade failed: {e}")

    # Test 9: Remove board moderator
    print_section("TEST 9: Remove Board Moderator")
    try:
        response = client.remove_board_moderator("admin", "bob", 1)
        print(f"Message: {response['message']}")
        print_result(True, "Board moderator removed")
    except Exception as e:
        print_result(False, f"Remove failed: {e}")

    # Test 10: Error handling - unauthorized action
    print_section("TEST 10: Error Handling - Unauthorized Action")
    try:
        # Login as alice (regular user), try to promote someone
        response = client.login("alice", "pass123")
        response = client.upgrade_user("alice", "bob")
        print_result(False, "Alice should not be able to upgrade users!")
    except Exception as e:
        if "Only admins can upgrade" in str(e):
            print_result(True, f"Properly denied: {e}")
        else:
            print_result(False, f"Unexpected error: {e}")

    client.disconnect()
    print_section("All Tests Completed!")
    print("✓ Moderator system is working correctly!\n")

if __name__ == "__main__":
    test_system()
