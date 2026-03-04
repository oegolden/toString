"""
gui.py — .toString(object) Messaging Platform
Reddit-inspired Tkinter GUI

ARCHITECTURE OVERVIEW:
─────────────────────────────────────────────────────────────────
  gui.py  ←→  client.py  ←→  server.py  ←→  messageBoard.py / user.py / toString.db
─────────────────────────────────────────────────────────────────

  This file handles ALL user-facing display and interaction.
  It calls functions from client.py (currently mocked by mock_client.py).

HOW TO INTEGRATE WITH client.py (for backend teammates):
  1. Ensure client.py exposes the same functions as mock_client.py
  2. Change the import line below from:
         import mock_client as client
     to:
         import client
  3. All functions called from this file are documented in mock_client.py
     with the expected request/response format.

LAYOUT STRUCTURE:
  App (Tk root)
  └── LoginFrame    — shown on startup; handles login + register
  └── MainFrame     — shown after login; the main app shell
       ├── Sidebar  — board list + subscribe/create controls
       └── FeedFrame
            ├── FeedView    — scrollable list of posts for selected board
            └── PostView    — expanded view of a single post + comments

CLASSES:
  App             — root window, manages which frame is visible
  LoginFrame      — login / register screen
  MainFrame       — post-login shell with sidebar + feed
  Sidebar         — left panel: board list, subscriptions, create board
  FeedFrame       — right panel: feed or post detail
  PostCard        — widget representing one post in the feed
  CommentCard     — widget representing one comment in a post
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import mock_client as client   # ← SWAP TO: import client  when backend is ready

# colors
BG_DARK     = "#a2a4a8"   # Main background
BG_MEDIUM   = "#6d819d"   # Cards, sidebar
BG_LIGHT    = "#6d9bda"   # Input fields, hover states
ACCENT      = "#ff4500"   # Reddit orange-red
ACCENT_DARK = "#cc3700"   # Hover for accent buttons
TEXT_PRI    = "#050709"   # Primary text
TEXT_SEC    = "#010101"   # Secondary / timestamps
TEXT_MUTED  = "#000000"   # Dividers, placeholders
BORDER      = "#002045"   # Card borders
SUCCESS     = "#3fb950"   # Subscribe / success green
DANGER      = "#f85149"   # Delete / error red

FONT_TITLE  = ("Ubuntu Condensed", 22, "bold")
FONT_BOARD  = ("Ubuntu Condensed", 13, "bold")
FONT_BODY   = ("Ubuntu Condensed", 11)
FONT_SMALL  = ("Ubuntu Condensed", 9)
FONT_META   = ("Ubuntu Condensed", 9, "italic")
FONT_BTN    = ("Ubuntu Condensed", 10, "bold")
FONT_INPUT  = ("Ubuntu Condensed", 11)


def make_button(parent, text, command, bg=ACCENT, fg=TEXT_PRI,
                padx=14, pady=5, font=FONT_BTN, **kwargs):
    """
    Returns a styled tk.Button.
    Use bg=SUCCESS for subscribe, bg=DANGER for delete/unsubscribe.
    """
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=ACCENT_DARK, activeforeground=fg,
        relief="flat", cursor="hand2", padx=padx, pady=pady,
        font=font, bd=0, **kwargs
    )
    # Hover effect
    hover_color = {ACCENT: ACCENT_DARK, SUCCESS: "#2ea043", DANGER: "#da3633",
                   BG_LIGHT: BORDER}.get(bg, bg)
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_color))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def make_label(parent, text, font=FONT_BODY, fg=TEXT_PRI, bg=BG_MEDIUM, **kwargs):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kwargs)


class App(tk.Tk):
    """
    Root window. Holds the current logged-in user's session state.
    Switches between LoginFrame and MainFrame.
    """
    def __init__(self):
        super().__init__()
        self.title(".toString(object)")
        self.geometry("1200x780")
        self.minsize(900, 600)
        self.configure(bg=BG_DARK)

        # Session state — populated on successful login
        self.current_user = None   # str: username
        self.user_role     = None  # str: "user" | "moderator" | "admin"

        # Show login screen first
        self._show_login()

    def _show_login(self):
        """Replace current content with the login/register frame."""
        for w in self.winfo_children():
            w.destroy()
        LoginFrame(self).pack(fill="both", expand=True)

    def on_login_success(self, username: str, role: str):
        """
        Called by LoginFrame after a successful login or register.
        Stores session info and switches to the main app frame.

        BACKEND INTEGRATION: 'role' comes from client.login() response dict.
        """
        self.current_user = username
        self.user_role     = role
        for w in self.winfo_children():
            w.destroy()
        MainFrame(self).pack(fill="both", expand=True)

    def logout(self):
        """Clear session and return to login screen."""
        self.current_user = None
        self.user_role     = None
        self._show_login()


# ═══════════════════════════════════════════════════════════════
#  LoginFrame — Login and registration screen
# ═══════════════════════════════════════════════════════════════
class LoginFrame(tk.Frame):
    """
    Shown on app startup. Handles login and new account registration.
    On success, calls app.on_login_success(username, role).
    """
    def __init__(self, master: App):
        super().__init__(master, bg=BG_DARK)
        self.app = master
        self._build()

    def _build(self):
        # Centered card
        card = tk.Frame(self, bg=BG_MEDIUM, bd=0, relief="flat",
                        highlightbackground=BORDER, highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center", width=420, height=480)

        # Logo / title
        tk.Label(card, text=".toString()", font=("Georgia", 28, "bold"),
                 fg=ACCENT, bg=BG_MEDIUM).pack(pady=(36, 4))
        tk.Label(card, text="A Text Platform", font=FONT_META,
                 fg=TEXT_SEC, bg=BG_MEDIUM).pack(pady=(0, 28))

        # Tab row: Login | Register
        self.tab_var = tk.StringVar(value="login")
        tab_row = tk.Frame(card, bg=BG_MEDIUM)
        tab_row.pack(fill="x", padx=32)

        self.login_tab_btn = tk.Button(
            tab_row, text="Log In", font=FONT_BTN,
            bg=BG_MEDIUM, fg=ACCENT, relief="flat", bd=0, cursor="hand2",
            command=lambda: self._switch_tab("login"))
        self.login_tab_btn.pack(side="left", padx=(0, 16))

        self.reg_tab_btn = tk.Button(
            tab_row, text="Register", font=FONT_BTN,
            bg=BG_MEDIUM, fg=TEXT_SEC, relief="flat", bd=0, cursor="hand2",
            command=lambda: self._switch_tab("register"))
        self.reg_tab_btn.pack(side="left")

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", padx=32, pady=8)

        # Input area (swaps between login / register)
        self.form_frame = tk.Frame(card, bg=BG_MEDIUM)
        self.form_frame.pack(fill="x", padx=32)
        self._build_login_form()

        # Error label
        self.err_var = tk.StringVar()
        tk.Label(card, textvariable=self.err_var, font=FONT_SMALL,
                 fg=DANGER, bg=BG_MEDIUM, wraplength=340).pack(pady=4)

    def _entry(self, parent, placeholder, show=None):
        """Create a styled entry field with placeholder text."""
        e = tk.Entry(parent, font=FONT_INPUT, bg=BG_LIGHT, fg=TEXT_PRI,
                     insertbackground=TEXT_PRI, relief="flat",
                     highlightbackground=BORDER, highlightthickness=1,
                     show=show)
        e.pack(fill="x", pady=4, ipady=8, padx=0)
        # Placeholder
        e.insert(0, placeholder)
        e.config(fg=TEXT_MUTED)
        def on_focus_in(ev):
            if e.get() == placeholder:
                e.delete(0, "end")
                e.config(fg=TEXT_PRI)
        def on_focus_out(ev):
            if not e.get():
                e.insert(0, placeholder)
                e.config(fg=TEXT_MUTED)
        e.bind("<FocusIn>", on_focus_in)
        e.bind("<FocusOut>", on_focus_out)
        return e

    def _build_login_form(self):
        for w in self.form_frame.winfo_children():
            w.destroy()
        self.user_entry = self._entry(self.form_frame, "Username")
        self.pass_entry = self._entry(self.form_frame, "Password", show="•")
        self.pass_entry.bind("<Return>", lambda e: self._do_login())
        make_button(self.form_frame, "LOG IN", self._do_login).pack(
            fill="x", pady=(12, 0), ipady=4)
        # Quick test-login hint
        tk.Label(self.form_frame, text="Test: alice / pass123  |  bob / pass456",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MEDIUM).pack(pady=(8, 0))

    def _build_register_form(self):
        for w in self.form_frame.winfo_children():
            w.destroy()
        self.user_entry   = self._entry(self.form_frame, "Choose a username")
        self.pass_entry   = self._entry(self.form_frame, "Password", show="•")
        self.pass2_entry  = self._entry(self.form_frame, "Confirm password", show="•")
        self.pass2_entry.bind("<Return>", lambda e: self._do_register())
        make_button(self.form_frame, "CREATE ACCOUNT", self._do_register).pack(
            fill="x", pady=(12, 0), ipady=4)

    def _switch_tab(self, tab: str):
        self.tab_var.set(tab)
        self.err_var.set("")
        if tab == "login":
            self.login_tab_btn.config(fg=ACCENT)
            self.reg_tab_btn.config(fg=TEXT_SEC)
            self._build_login_form()
        else:
            self.login_tab_btn.config(fg=TEXT_SEC)
            self.reg_tab_btn.config(fg=ACCENT)
            self._build_register_form()

    def _get_entry(self, entry, placeholder):
        """Return entry text, or empty string if still showing placeholder."""
        val = entry.get()
        return "" if val == placeholder else val

    def _do_login(self):
        username = self._get_entry(self.user_entry, "Username")
        password = self._get_entry(self.pass_entry, "Password")
        if not username or not password:
            self.err_var.set("Please enter both username and password.")
            return
        try:
            # ── BACKEND CALL ──────────────────────────────────────────────
            # client.login() sends credentials over socket and returns:
            # {"username": str, "role": "user"|"moderator"|"admin"}
            result = client.login(username, password)
            # ─────────────────────────────────────────────────────────────
            self.app.on_login_success(result["username"], result["role"])
        except Exception as e:
            self.err_var.set(str(e))

    def _do_register(self):
        username = self._get_entry(self.user_entry, "Choose a username")
        password = self._get_entry(self.pass_entry, "Password")
        confirm  = self._get_entry(self.pass2_entry, "Confirm password")
        if not username or not password:
            self.err_var.set("All fields are required.")
            return
        if password != confirm:
            self.err_var.set("Passwords do not match.")
            return
        try:
            # ── BACKEND CALL ──────────────────────────────────────────────
            # client.register() sends new credentials to server, returns user dict
            result = client.register(username, password)
            # ─────────────────────────────────────────────────────────────
            self.app.on_login_success(result["username"], result["role"])
        except Exception as e:
            self.err_var.set(str(e))

if __name__ == "__main__":
    app = App()
    app.mainloop()