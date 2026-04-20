# toString

A Reddit-inspired, group messaging board platform for CS 138 System Security. Built with Python featuring comprehensive authentication, authorization, content moderation, and audit logging.

## Quick Start

```bash
#generate cert and server key
python3 generate_cert.py

# Start server in one terminal
python3 server.py 1234

# Start the GUI in another terminal
python3 gui.py
```

## 📋 Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [User Guide](#user-guide)
- [Security Features](#security-features)
- [Database Schema](#database-schema)
- [Audit Logging](#audit-logging)


---

## ✨ Features

### Authentication & Authorization
- User registration with password strength validation (NIST 800-63B compliant)
- Secure login with audit logging (success/failures, IP, device, timestamp)
- Role-based access control (User, Moderator, Admin)
- Password reset functionality
- System-wide moderators and board-specific moderators

### Message Board Features
- Create and manage message boards (r/ naming convention)
- Subscribe/unsubscribe from boards
- Post messages and comments
- Edit/delete messages (with authorization checks)
- Board discovery and home feed

### Moderation System
- User role management (promote/demote users to moderators)
- Board-specific moderator assignment
- Message deletion by authors, board moderators, or admins
- Audit logging for all moderator actions
- Admin panel for moderation management

### Content Moderation
- Automatic harmful content detection and flagging
- Profanity checking
- Spam pattern detection
- Suspicious keyword detection
- Excessive capitalization detection

### Audit & Security Logging
- **Login Logs:** Track all login attempts with IP, device, status
- **Post Logs:** Track posts with harmful content flags and IP addresses
- **Moderator Logs:** Track all moderator actions with IP and device info
- **General Audit Trail:** All security-relevant actions timestamped and logged

### User Interface
- Modern Tkinter GUI with Reddit-like layout
- Server connection configuration (IP & port)
- Real-time password strength validation
- Admin panel with moderation tools
- Audit log viewer with pagination
---

## 📦 Requirements

### System Requirements
- **Python:** 3.8 or higher
- **OS:** macOS, Linux, or Windows
- **Database:** SQLite (included with Python)

### Python Dependencies
```
tk (Tkinter) - usually included with Python
zxcvbn       - password strength estimation
```

### Optional Dependencies
```
aiosqlite    - async database operations (future feature)
aiosqlitepool - connection pooling (future feature)
```

---

## 🔧 Installation

### Step 1: Clone or Download the Project

```bash
# If using git
git clone <repository-url>
cd .toString--1

Convert to PDF: `pandoc docs/assurance.md -o docs/assurance.pdf` (or use your preferred tool)
# Or download as zip and extract
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install zxcvbn
```

**Note:** Python's `tkinter` and `sqlite3` are included by default. If you're on Linux and don't have tkinter:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter
```

### Step 4: Initialize the Database

```bash
python3 setupdb.py
```

This creates `toString.db` with the necessary tables.

---

## ⚙️ Configuration

### Server Configuration

The server runs on a configurable port (default: 1234).

```bash
# Start server on default port
python3 server.py 1234

# Start server on custom port
python3 server.py 5000
```

**Port Requirements:**
- Must be between 1024 and 65535
- Ensure no firewall blocks the port
- For network access, binding is available at 0.0.0.0

### Client Configuration

The GUI application provides an interactive server configuration dialog:

1. Start `gui.py`
2. Enter the server IP address (default: 127.0.0.1)
3. Enter the server port (default: 1234)
4. Click "Connect" or "Use Defaults"

**Connection Timeout:** 5 seconds

---

## 🚀 Quick Start

### Running Locally (Same Machine)

**Terminal 1 - Start Server:**
```bash
python3 server.py 1234
```

Expected output:
```
Hello. Created new process with listening port 1234
Started thread input_handler_thread
Started thread connection_thread
Started thread request_handler_thread
```

**Terminal 2 - Start Client:**
```bash
python3 gui.py
```

1. Connection Configuration dialog appears
2. Click "Use Defaults (127.0.0.1:1234)" or enter custom settings
3. Login/Register screen appears
4. Test login: alice / pass123

### Running on Different Machines

**Server Machine:**
```bash
python3 server.py 1234
# Server is now listening on all interfaces
```

**Client Machine:**
```bash
python3 gui.py
# Enter server's IP address when prompted (e.g., 192.168.1.100)
# Enter port 1234
```

---

## 👤 User Guide

### Creating an Account
1. Click "REGISTER" tab
2. Enter username (3+ characters recommended)
3. Enter password (4+ characters, NIST compliant)
4. Confirm password
5. Password strength indicator shows requirements
6. Click "CREATE ACCOUNT"

### Logging In
1. Enter credentials
2. Click "LOG IN" or press Enter
3. On first login, subscribe to boards

### Using Boards
- **Home:** Posts from subscribed boards
- **Discover:** Browse and subscribe to new boards
- **Subscribe:** Click "Join Board"
- **Post:** Type in compose box and click "POST"

### Admin Features
- Click "Admin Panel" button (visible to admins only)
- **Promote Tab:** Upgrade users to system moderators
- **Board Mods Tab:** Assign board moderators
- **Audit Logs Tab:** View system audit trail

### Password Reset
1. Click "Forgot your password?" on login screen
2. Enter username and new password
3. Click "Reset Password"
4. Log in with new credentials

---

## 🔒 Security Features

### Authentication
- NIST 800-63B compliant password validation
- Login attempt tracking with IP/device
- Password reset functionality
- Session management

### Authorization
- Three-tier role system: User, Moderator, Admin
- Board-specific moderator permissions
- Message ownership verification
- Audit-based access decisions

### Content Moderation
- Automatic harmful content detection
- Profanity filtering
- Spam detection
- Flagging system for admin review

### Audit Logging
All actions logged with:
- Timestamp
- User ID
- IP address
- Device information
- Action type
- Success/failure status

---

## 📊 Database Schema

### Key Tables
- **users:** Authentication and role management
- **messageBoard:** Board data with creation info
- **messages:** Post content with metadata
- **board_moderators:** Moderator assignments
- **audit_logs:** Security event trail
- **login_logs:** Authentication tracking
- **post_logs:** Content tracking with harmful flags

---

## 📝 Audit Logging

### Events Tracked
- User login attempts (success & failure)
- User registration
- Password resets
- Message posts/edits/deletes
- User role changes
- Board moderator assignments
- Audit log queries

### Log Format
```
[ACTION_TYPE] actor_username | Status: SUCCESS/FAILED | IP: 192.168.1.x | Device: Python-Client
```
---

### Running Tests
```bash
pytest
pytest -v
pytest --cov=.
```
