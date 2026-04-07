# toString

A secure text-based group messaging board platform for CS 138 System Security.

## Quick Start

```bash
# Start server in one terminal
python3 server.py 1234

# Run GUI (in another terminal)
python3 gui.py

```

This launches the GUI, which automatically connects to the server on localhost:1234.

The GUI will load the login screen. You can log in with test credentials:
    Username: alice    Password: pass123
    Username: bob      Password: pass456
    Username: admin    Password: admin


SERVER CONSOLE COMMANDS
-----------------------
While the server is running, you can type these commands in the server terminal:

    help      - Show available commands
    myip      - Display server IP address
    myport    - Display listening port
    list      - Show active client connections
    exit      - Shutdown server

## Project Structure

- `client.py` — Client (swap with mock_client for development)
- `server.py` — Socket server
- `mock_client.py` — Mock backend for GUI development and testing
- `gui.py` — Tkinter GUI
- `tests/` — Pytest test suite (auth, authorization, messaging, DB security, audit)
- `docs/` — assurance.md, design.md, requirements.md (sources for PDFs)

## Documentation

- **assurance.md** — How the system was tested
- **design.md** — Security design (authentication, authorization, audit, confidentiality, integrity)
- **requirements.md** — System backlog, threat model, security goals

Convert to PDF: `pandoc docs/assurance.md -o docs/assurance.pdf` (or use your preferred tool)