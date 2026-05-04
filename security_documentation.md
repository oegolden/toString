---
marp: true
theme: default
paginate: true
style: |
  section { font-size: 22px; }
  pre { font-size: 15px; }
  h1 { color: #2c3e50; }
  h2 { color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 4px; }
  table { font-size: 18px; }
  code { background: #f4f4f4; }
---

# .toString(object)
## CS 138 Security Documentation

**A secure, Reddit-style message-board application**

ogolden@g.hmc.edu | Harvey Mudd College

---

## System Purpose

`.toString(object)` is a **Reddit-style message-board** built on a custom TCP/SSL server.

**Core features:**
- Register accounts, log in, recover passwords via email
- Create and subscribe to topical boards
- Post, edit, delete messages and comments
- Tiered role system: **user → moderator → admin**
- Automated content moderation on every submission

**Security-first design:**
- All traffic encrypted over TLS
- Passwords never stored in plaintext
- Every security-relevant event written to structured audit logs
- All database queries parameterised (no string interpolation)

---

## System Architecture

```
Client ──TLS──► Server (server.py)
                 │
                 ├─ Auth layer       → user.py        → users table
                 ├─ Board/Message    → messageBoard.py → messageBoard + messages tables
                 ├─ Content check    → content_moderation.py
                 ├─ Audit            → log functions  → login_logs / audit_logs / post_logs
                 └─ DB pool          → utils/sqlService.py → toString.db (SQLite / aiosqlite)
```

**Key files:**
| File | Role |
|------|------|
| `server.py` | TCP/TLS server, request dispatch, in-memory session state |
| `user.py` | DB-backed user registration, login, password reset |
| `messageBoard.py` | DB-backed board and message persistence |
| `setupdb.py` | Schema definition (users, messages, boards, audit tables) |
| `content_moderation.py` | Profanity / spam / suspicious-content engine |

---

## System Backlog — Completed

| User type | Importance | User story |
|-----------|------------|------------|
| Any | **M** | Register with username, password, email |
| Any | **M** | Log in / log out; at most one active session |
| Any | **M** | Request a recovery code by email; reset password |
| user | **M** | List, create, subscribe to / unsubscribe from boards |
| user | **M** | Post, edit, delete own messages; comment on messages |
| moderator | **M** | Delete any message on boards they moderate |
| admin | **M** | Promote/demote users; assign/remove board moderators |
| admin | **M** | Retrieve categorised audit logs |
| Any | **S** | Content moderation: profanity, spam, suspicious keywords blocked |
| Any | **S** | Duplicate concurrent sessions rejected |

**M** = Must have · **S** = Should have

---

## Threat Model

| Adversary | Motivation | Capabilities |
|-----------|------------|--------------|
| **Network attacker** | Eavesdrop credentials / messages; inject data | Observe / intercept TCP traffic; cannot break TLS or PBKDF2 |
| **Malicious user** | Access other accounts; post prohibited content; escalate privileges | Valid account; knowledge of client protocol; arbitrary request strings |
| **Credential-stuffing bot** | Gain access via leaked password lists | Many rapid login attempts |
| **Rogue moderator** | Abuse elevated privileges; delete legitimate content | Moderator account; cannot read password hashes or self-promote to admin |

**Non-threats (out of scope):**
- Physical server access (assumed controlled environment)
- OS / Python runtime compromise
- Network-layer denial-of-service

---

## Security Goals

| ID | Category | Goal |
|----|----------|------|
| G1 | **Confidentiality** | Passwords never stored or transmitted in plaintext |
| G2 | **Confidentiality** | All client–server communication encrypted in transit |
| G3 | **Confidentiality** | Users cannot read private data belonging to other users |
| G4 | **Integrity** | A user cannot authenticate as another without knowing their password |
| G5 | **Integrity** | Only the author, a board moderator, or an admin may delete a message |
| G6 | **Integrity** | Only an admin may promote users or assign board moderators |
| G7 | **Integrity** | Message content validated before storage (no injection) |
| G8 | **Integrity** | Board / message content screened by content-moderation engine |
| G9 | **Availability** | At most one active session per account at a time |
| G10 | **Availability** | All security-relevant events written to audit logs |

---

## Authentication — Password Hashing

Passwords are stored using **PBKDF2-HMAC-SHA-256**, 100 000 iterations, 16-byte random salt.

```python
# user.py
def _hash_password(password: str, salt: bytes = None) -> str:
    if salt is None:
        salt = os.urandom(16)          # fresh random salt per registration
    hash_bytes = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt, 100_000
    )
    return salt.hex() + '$' + hash_bytes.hex()   # stored: "<salt>$<hash>"

def _verify_password(stored: str, provided: str) -> bool:
    salt_hex, hash_hex = stored.split('$')
    salt = bytes.fromhex(salt_hex)
    return hashlib.pbkdf2_hmac(
        'sha256', provided.encode('utf-8'), salt, 100_000
    ).hex() == hash_hex
```

- Same algorithm in `user.py` (DB layer) and `server.py` (session layer) — hashes are interoperable
- Two users with the same password have **different stored values** (random salt)
- **Addresses:** G1, G4

---

## Authentication — Transport & Session Management

**TLS encryption**
```python
# server.py — startup
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile="server.crt", keyfile="server.key")
s = context.wrap_socket(s, server_side=True)
```
- Self-signed cert generated at startup by `generate_cert.py` (RSA-2048, SHA-256)
- All bytes between client and server are encrypted — no credential travels in plaintext
- **Addresses:** G2

**Session management**
```python
# server.py — LOGIN handler
if username in _live_users:
    log_login(username, client_ip, device_info, False, "User already logged in")
    send_error(return_socket, "User already logged in")
    return
_live_users[username] = {"login_time": time.time(), "ip_address": client_ip}
```
- `_live_users` tracks active sessions; duplicate login rejected and **logged**
- **Addresses:** G9

---

## Authentication — Password Recovery

```python
# user.py
def send_recovery_email(self):
    recovery_code = os.urandom(16).hex()   # 128-bit random, single-use
    msg = EmailMessage()
    msg['To'] = self.email
    msg.set_content(f"Reset code: {recovery_code}")
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls(context=ssl.create_default_context())   # encrypted SMTP
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
    return recovery_code
```

**Flow:**
1. Client sends `SEND_RECOVERY_EMAIL <username> <email>`
2. Server generates code, emails it, stores it in `_recovery_codes[username]`
3. Client sends `RESET_PASSWORD <username> <email> <code> <new_password>`
4. Server verifies code, calls `user.reset_password(new_password)` (hashes before storing), **deletes** code

---

## Authorization — Role Hierarchy

```
admin
  └─ system-wide moderator rights + user management + audit log access
moderator
  └─ delete any message on assigned boards
user
  └─ post / edit / delete own content on subscribed boards
```

**Enforcement — server-side checks on every request:**

```python
# server.py — DELETE_MESSAGE handler
is_author        = msg["author"] == username
is_board_mod     = is_user_moderator_of_board(username, board_id)
is_admin         = _users.get(username, {}).get("role") == "admin"

if not (is_author or is_board_mod or is_admin):
    send_error(return_socket, "You can only delete your own messages, "
               "or manage messages on boards you moderate")
    return
```

- Persistence layer (`MessageBoard.delete_message`) adds a **creator-only** guard at the DB level
- Privilege escalation routes (`UPGRADE_USER`, `ASSIGN_BOARD_MODERATOR`) gated on `role == "admin"`
- **Addresses:** G5, G6

---

## Audit Logging

Five dedicated log structures capture every security-relevant event:

| Log table | Trigger | Key fields |
|-----------|---------|------------|
| `login_logs` | Every login attempt | username, ip_address, success, failure_reason, timestamp |
| `audit_logs` | Role changes, admin actions | action, performed_by, target_user, board_id, details, success |
| `post_logs` | Every post / comment / deletion | user_id, board_id, content_preview, flagged_harmful, action |
| `board_moderators` | Moderator assignment / removal | user_id, board_id, assigned_at |
| `moderator_requests` | Role-upgrade requests | requesting_user, request_type, status |

```python
# server.py — login failure audit
log_login(username, client_ip, device_info, False, "Invalid password")
# → stored in login_logs with timestamp, IP, reason
```

- IP address captured from every connection socket
- Audit log access is **admin-only**; unauthorised attempts are themselves logged
- **Addresses:** G10

---

## Confidentiality

**At rest — password hashing**
- PBKDF2 with 100 000 iterations: brute-forcing one hash costs 100 000 SHA-256 evaluations
- Per-user random salt: rainbow tables are ineffective
- The plaintext password is never written to disk or logs

**In transit — TLS**
- Every TCP byte is encrypted before leaving the process
- Client disables hostname verification for the self-signed cert (acceptable for a local testbed; a production deployment uses a CA-signed certificate)

**Data scoping — minimal responses**
```python
# server.py — LOGIN response (only username + role, never hash or email)
send_json(return_socket, {"username": username, "role": _users[username]["role"]})
```

- Audit logs readable by admins only
- Password hashes never appear in any API response

**Addresses:** G1, G2, G3

---

## Integrity — SQL Injection Prevention

Every database interaction uses **parameterised queries** (`?` placeholders via `aiosqlite`).
User-supplied strings are never interpolated into SQL.

```python
# user.py — register
await conn.execute(
    "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
    (self.username, self.email, _hash_password(password))   # ← bound, not interpolated
)

# messageBoard.py — load board
cursor = await conn.execute(
    "SELECT mb.board_id FROM messageBoard mb "
    "JOIN users u ON mb.creator_id = u.user_id "
    "WHERE mb.name = ? AND u.username = ?",
    (name, creator)
)
```

**Verified by test:**
```python
# test_persistence.py
def test_sql_injection_in_password_stored_safely(self):
    run(_make_user("alice", password="'; DROP TABLE users; --"))
    assert run(User("alice", ...).login("'; DROP TABLE users; --")) is True
    assert run(User("alice", ...).login("innocent")) is False
    # Table intact — a second user can still be registered
    run(_make_user("bob"))
```

**Addresses:** G7

---

## Integrity — Content Moderation

Every message, comment, and board name/description passes through `ContentModerator.moderate()` before storage.

```python
# server.py — POST_MESSAGE handler
moderator = get_content_moderator()
flagged, reason = moderator.moderate(content)
if flagged:
    send_error(return_socket, f"Comment violates content policy: {reason}")
    log_audit("POST_MESSAGE", username, details=f"Rejected: {content}", success=False)
    return
```

**Checks performed (in order):**

| Check | Threshold | Example trigger |
|-------|-----------|-----------------|
| Profanity | `profanity-check2` ML model + keyword fallback | Offensive words |
| Spam patterns | Regex on URL, "buy now", casino | `http://`, `BUY NOW` |
| Suspicious keywords | ≥ 2 of: hate, kill, attack, threat | "kill + attack" |
| Excessive caps | > 50% uppercase alpha | `SHOUTING MESSAGE` |
| Excessive special chars | > 30% of total chars | `!!!@@@###$$$` |

**Addresses:** G8

---

## Assurance — Test Suite

86 automated tests across 9 files. Run with `pytest` from the project root.

| File | Scope | Tests |
|------|-------|-------|
| `test_auth.py` | Registration, login (mock) | 11 |
| `test_authorization.py` | Edit/delete/subscription permissions | 13 |
| `test_messaging.py` | Post, comment, board creation | 7 |
| `test_database_security.py` | SQL injection, special-character safety | 7 |
| `test_audit.py` | Audit event trackability | 7 |
| **`test_persistence.py`** | **Real SQLite — User and MessageBoard CRUD** | **35** |
| `test_integration_server.py` | End-to-end over real TLS socket | 1 |
| `test_password_recovery.py` | Recovery code + password reset | 2 |
| `test_ssl_*.py` | TLS handshake verification | 2 |

**Test isolation:** every `test_persistence.py` test gets a fresh `tmp_path` SQLite database, a clean schema, and a monkeypatched connection pool — no shared state, no test-order dependency.

---

## Assurance — Security-Specific Tests

**SQL injection (real DB):**
```python
def test_sql_injection_in_username_treated_as_literal(self):
    run(_make_user("'; DROP TABLE users; --"))  # stored as literal string
    run(_make_user("alice"))                    # table still intact
    assert run(User("alice", ...).login("password123")) is True
```

**Password hashing:**
```python
def test_password_is_hashed_not_stored_plaintext(self):
    run(_make_user("alice"))
    # If stored plaintext, comparing "wrong" == "password123" would succeed
    # PBKDF2 verification makes it fail correctly
    assert run(User("alice", ...).login("wrong")) is False
```

**Permission enforcement (real DB):**
```python
def test_non_creator_raises_permission_error(self):
    run(_make_user("alice"))
    run(_make_user("bob", email="bob@test.com"))
    board = run(MessageBoard.load("alice", "r/Test"))
    msg_id = run(board.add_message("Hello", "alice"))
    with pytest.raises(PermissionError):
        run(board.delete_message("bob", msg_id))
```

---

## Assurance — Build-Time Gating

Tests run **inside the Docker build**. A broken server image cannot be produced.

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /server

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate SSL certs and initialise the database schema
RUN python generate_cert.py && python setupdb.py

# Build fails here if any test fails — broken image cannot be deployed
RUN python -m pytest

EXPOSE 1234
CMD ["python", "server.py", "1234"]
```

**Additional quality measures:**
- `server.py` checks `sys.stdin.isatty()` before entering the admin input loop — prevents log spam under test or container environments
- `pytest.ini` sets `testpaths = tests` and `addopts = -v` so `pytest` with no arguments always runs the full suite

---

## Ethical Considerations

**Content moderation vs. free expression**
- Automated moderation risks over-blocking (false positives) and under-blocking (evasion)
- Rejection messages tell the user the specific reason — reducing platform power asymmetry
- Keyword lists and thresholds are configurable; community standards can be adjusted without code changes

**Privacy and audit data**
- IP addresses and device identifiers are captured in every audit record — necessary for incident forensics, but a privacy risk if the log is exfiltrated
- Audit log access restricted to administrators
- A production deployment should encrypt the audit log at rest and enforce retention / rotation policies

**Role abuse**
- Moderators can delete any content on their boards; admins can promote anyone
- Every such action is written to `audit_logs` with the actor's identity and the target — accountability without blocking legitimate moderation

**Honest failure messages**
- Login failures report the specific reason ("User does not exist" vs "Invalid password")
- This aids legitimate users at the cost of slight username enumumerability
- The specific reason is **also** captured in the audit log, so security monitoring is unaffected

**Password recovery trust boundary**
- Recovery codes are transmitted via SMTP/STARTTLS — protected in transit
- Codes are single-use and deleted on use
- Security ultimately depends on the user's email account — an external dependency the system cannot control

---

## Summary

| Element | Mechanism |
|---------|-----------|
| **Authentication** | PBKDF2-SHA256 (100k iter, random salt) · TLS · single-session enforcement · SMTP recovery codes |
| **Authorization** | RBAC (user / moderator / admin) · per-handler checks · board-level moderator table |
| **Audit** | 5 log tables (login, audit, post, moderator, requests) · IP + timestamp on every record |
| **Confidentiality** | TLS in transit · hashed passwords at rest · minimal API responses |
| **Integrity** | Parameterised queries · content-moderation engine · input validation |

**86 tests · real-DB persistence suite · build-time test gating in Docker**
