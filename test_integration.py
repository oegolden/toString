#!/usr/bin/env python3
"""
test_integration.py - simple test to verify client-server integration

Run this to test that the client.py and server.py work together correctly.
Outline of test:
1. Starts the server on port 9999
2. Connects a client to the server
3. Tests several operations (login, get boards, create board, etc.)
4. Verify responses match expected formats
"""

import subprocess
import time
import sys
import client

def test_integration():
    """Run integration tests."""
    print("=" * 60)
    print("Starting integration test...")
    print("=" * 60)
    
    # start server in background
    print("\n[1/5] Starting server on port 9999...")
    server_proc = subprocess.Popen(
        [sys.executable, "server.py", "9999"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # give server time to start
    
    try:
        print("[2/5] Connecting client to server...")
        client.connect("127.0.0.1", 9999)
        print("      ✓ Connected successfully")
        
        # test login
        print("\n[3/5] Testing login...")
        try:
            result = client.login("alice", "pass123")
            assert result["username"] == "alice"
            assert result["role"] == "user"
            print(f"      ✓ Login successful: {result}")
        except Exception as e:
            print(f"      ✗ Login failed: {e}")
            return False
        
        # test get all boards
        print("\n[4/5] Testing get all boards...")
        try:
            boards = client.get_all_boards()
            assert isinstance(boards, list)
            assert len(boards) > 0
            print(f"      ✓ Got {len(boards)} boards:")
            for board in boards[:3]:
                print(f"        - {board['name']}: {board['description']}")
        except Exception as e:
            print(f"      ✗ Get boards failed: {e}")
            return False
        
        # test get subscribed boards
        print("\n[5/5] Testing get subscribed boards...")
        try:
            sub_boards = client.get_subscribed_boards("alice")
            assert isinstance(sub_boards, list)
            print(f"      ✓ Got {len(sub_boards)} subscribed boards")
        except Exception as e:
            print(f"      ✗ Get subscribed boards failed: {e}")
            return False
        
        client.disconnect()
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # clean up server
        print("\nShutting down server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()

if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
