# toString

A secure text-based group messaging board platform for CS 138 System Security.

## Quick Start

```bash
# Run GUI (uses mock backend)
python3 gui.py

# Run tests
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -v
```

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