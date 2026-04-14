"""
gui.py — .toString(object) Messaging Platform
Reddit-inspired Tkinter GUI

ARCHITECTURE OVERVIEW:
─────────────────────────────────────────────────────────────────
  gui.py  ←→  client.py  ←→  server.py  ←→  messageBoard.py / user.py / toString.db
─────────────────────────────────────────────────────────────────

  This file handles ALL user-facing display and interaction.
  It calls functions from client.py (currently mocked by mock_client.py).

HOW TO INTEGRATE WITH client.py (for backend when working):
  1. client.py should have the same functions as mock_client.py
  2. Change the import line below from:
         import mock_client as client
     to:
         import client
  3. All functions called from this file are documented in mock_client.py
     with the expected request/response format.
  4. Look for "BACKEND TO FIX" comments to see where backend functions are used.

LAYOUT:
  App (Tkinter root)
  └── LoginFrame    — shown on startup; handles login + register
  └── MainFrame     — shown after login; the main app
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
import client   # Real backend integration
import re
from zxcvbn import zxcvbn

# colors
BG_DARK     = "#e4e4e4"   # Main background
BG_MEDIUM   = "#f7f7f7"   # Cards, sidebar
BG_LIGHT    = "#abb5c2"   # Input fields, hover states
ACCENT      = "#060606"   
ACCENT_DARK = "#000000"   
TEXT_PRI    = "#050709"   # Primary text
TEXT_SEC    = "#010101"   # Secondary / timestamps
TEXT_MUTED  = "#000000"   # Dividers, placeholders
BORDER      = "#626262"   # Card borders
SUCCESS     = "#3fb950"   # Subscribe / success green
DANGER      = "#f85149"   # Delete / error red

FONT_TITLE  = ("Ubuntu Condensed", 22, "bold")
FONT_BOARD  = ("Ubuntu Condensed", 13, "bold")
FONT_BODY   = ("Ubuntu Condensed", 11)
FONT_SMALL  = ("Ubuntu Condensed", 9)
FONT_META   = ("Ubuntu Condensed", 9, "italic")
FONT_BTN    = ("Ubuntu Condensed", 10, "bold")
FONT_INPUT  = ("Ubuntu Condensed", 11)

class PasswordStrengthChecker:
    """
    NIST 800-63B compliant password strength checker.
    Uses zxcvbn for realistic strength estimation and prioritizes length.
    """

    # Common blocklist (can be expanded or loaded from a file)
    # These are examples; in production, use a more comprehensive list.
    COMMON_PASSWORDS = {
        "password", "password1", "123456", "12345678", "qwerty", "abc123",
        "monkey", "letmein", "dragon", "baseball", "iloveyou", "trustno1",
        "sunshine", "master", "hello", "football", "welcome", "admin",
        "user", "login", "password123", "admin123", "passw0rd", "password!"
    }

    # NIST criteria messages (positive, encouraging)
    RULES = [
        ("At least 8 characters long", lambda pwd, info: len(pwd) >= 8),
        ("Not a commonly used password", lambda pwd, info: pwd.lower() not in PasswordStrengthChecker.COMMON_PASSWORDS),
        ("Not easily guessed (zxcvbn score ≥ 3)", lambda pwd, info: info.get('score', 0) >= 3),
        ("Length is your friend — consider a passphrase", lambda pwd, info: len(pwd) >= 12),  # Bonus for length
    ]

    def __init__(self, master, password_var, confirm_var):
        self.master = master
        self.password_var = password_var
        self.confirm_var = confirm_var

        # --- UI Elements ---
        self.checker_frame = tk.Frame(master, bg=BG_MEDIUM)
        self.checker_frame.pack(fill="x", pady=(8, 0))

        # Progress bar (thin canvas rectangle)
        self.progress_canvas = tk.Canvas(
            self.checker_frame, height=4, bg=BG_LIGHT,
            highlightthickness=0, relief="flat"
        )
        self.progress_canvas.pack(fill="x", pady=(0, 8))
        self.progress_rect = self.progress_canvas.create_rectangle(
            0, 0, 0, 4, fill=BG_LIGHT, width=0
        )

        # Strength label
        self.strength_label = tk.Label(
            self.checker_frame, text="", font=FONT_SMALL,
            fg=TEXT_SEC, bg=BG_MEDIUM
        )
        self.strength_label.pack(anchor="w", pady=(0, 6))

        # Rule checklist (dynamic based on NIST)
        self.rule_labels = []
        for rule_text, _ in self.RULES:
            label = tk.Label(
                self.checker_frame, text=f"✗ {rule_text}",
                font=FONT_SMALL, fg=DANGER, bg=BG_MEDIUM,
                anchor="w", wraplength=300, justify="left"
            )
            label.pack(fill="x", pady=2)
            self.rule_labels.append(label)

        # Bind to password variable
        self.password_var.trace_add("write", self._on_password_change)

    def _evaluate(self, password):
        """Evaluate password against NIST criteria using zxcvbn."""
        # Get zxcvbn feedback
        result = zxcvbn(password) if password else {"score": 0, "feedback": {}}
        info = {
            "score": result["score"],
            "feedback": result.get("feedback", {}),
            "guesses": result.get("guesses", 0)
        }

        passed_rules = []
        for rule_text, rule_func in self.RULES:
            passed = rule_func(password, info)
            passed_rules.append(passed)
        score = sum(passed_rules)  # Score 0-4 based on NIST rules

        return score, passed_rules, info

    def _on_password_change(self, *args):
        """Called when password changes. Updates UI and returns strength."""
        password = self.password_var.get()
        confirm = self.confirm_var.get()

        # Evaluate password
        score, passed_rules, info = self._evaluate(password)

        # Update rule checklist UI
        for i, (rule_text, _) in enumerate(self.RULES):
            if passed_rules[i]:
                self.rule_labels[i].config(text=f"✓ {rule_text}", fg=SUCCESS)
            else:
                self.rule_labels[i].config(text=f"✗ {rule_text}", fg=DANGER)

        # Update progress bar and strength label
        self._update_progress(score, len(passed_rules))
        self._update_strength_label(score, info)

        # Return: is_strong_enough (score >= 2 means meets minimum NIST length + not common)
        # Score >= 2 corresponds to: length >= 8 AND not common password.
        # You can adjust the threshold (e.g., require score >= 3 for stronger).
        is_strong_enough = score >= 2
        return score, is_strong_enough

    def _update_progress(self, score, max_score):
        """Update progress bar color and width based on NIST score (0-4)."""
        if max_score == 0:
            return
        width_percent = score / max_score
        canvas_width = self.progress_canvas.winfo_width()

        if canvas_width > 1:
            rect_width = int(canvas_width * width_percent)
            self.progress_canvas.coords(self.progress_rect, 0, 0, rect_width, 4)

        # Color mapping: Red → Yellow → Green
        if score <= 1:
            color = DANGER
        elif score <= 2:
            color = "#f39c12"  # Orange
        else:
            color = SUCCESS

        self.progress_canvas.itemconfig(self.progress_rect, fill=color)

        if canvas_width <= 1:
            self.master.after(100, lambda: self._update_progress(score, max_score))

    def _update_strength_label(self, score, info):
        """Set strength text and color based on NIST score."""
        if score <= 0:
            text = "Very Weak"
            color = DANGER
        elif score == 1:
            text = "Weak"
            color = DANGER
        elif score == 2:
            text = "Fair"
            color = "#f39c12"
        elif score == 3:
            text = "Good"
            color = "#f1c40f"
        else:
            text = "Strong"
            color = SUCCESS

        # Add zxcvbn warning if available and score is low
        warning = info.get('feedback', {}).get('warning', '')
        display_text = f"Strength: {text}"
        if warning and score < 3:
            display_text += f" – {warning}"

        self.strength_label.config(text=display_text, fg=color)

    def update_submit_button(self, submit_button):
        """Enable/disable submit button based on NIST password strength and confirmation match."""
        password = self.password_var.get()
        confirm = self.confirm_var.get()

        if password:
            _, is_strong_enough = self._on_password_change()
            if is_strong_enough and password == confirm:
                submit_button.config(state="normal")
            else:
                submit_button.config(state="disabled")
        else:
            submit_button.config(state="normal")

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

        # Initialize client connection to server
        try:
            client.connect("127.0.0.1", 1235)
        except Exception as e:
            messagebox.showerror(
                "Connection Error",
                f"Failed to connect to server:\n{str(e)}\n\nMake sure the server is running on port 1234."
            )
            self.destroy()
            return

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


class LoginFrame(tk.Frame):
    """
    Shown on app startup. Handles login and new account registration.
    On success, calls app.on_login_success(username, role).
    """
    def __init__(self, master: App):
        super().__init__(master, bg=BG_DARK)
        self.app = master
        self.password_checker = None  # Will be initialized in register form
        self._build()
    
    def _build(self):
        # Centered card
        card = tk.Frame(self, bg=BG_MEDIUM, bd=1, relief="flat")
        card.place(relx=0.5, rely=0.5, anchor="center", width=420, height=550)  # Increased height for password checker

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
            bg=BG_MEDIUM, relief="flat", bd=1, cursor="hand2",
            command=lambda: self._switch_tab("login"))
        self.login_tab_btn.pack(side="left", padx=(0, 16))

        self.reg_tab_btn = tk.Button(
            tab_row, text="Register", font=FONT_BTN,
            bg=BG_MEDIUM, relief="flat", bd=0, cursor="hand2",
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

    def _entry(self, parent, placeholder, show=None, textvariable=None):
        """Create a styled entry field with placeholder text."""
        e = tk.Entry(parent, font=FONT_INPUT, bg=BG_LIGHT, fg=TEXT_PRI,
                     insertbackground=TEXT_PRI, relief="flat",
                     highlightbackground=BORDER, highlightthickness=1,
                     show=show, textvariable=textvariable)
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
    
    def _get_entry(self, entry, placeholder):
        """Return entry text, or empty string if still showing placeholder."""
        val = entry.get()
        return "" if val == placeholder else val
    
    def _build_login_form(self):
        for w in self.form_frame.winfo_children():
            w.destroy()
        self.user_entry = self._entry(self.form_frame, "Username")
        self.pass_entry = self._entry(self.form_frame, "Password", show="•")
        self.pass_entry.bind("<Return>", lambda e: self._do_login())
        make_button(self.form_frame, "LOG IN", self._do_login).pack(
            fill="x", pady=(12, 0), ipady=4)
        # Quick test-login hint
        tk.Label(self.form_frame, text="Test: alice / pass123",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_MEDIUM).pack(pady=(8, 0))

    def _build_register_form(self):
        for w in self.form_frame.winfo_children():
            w.destroy()
        
        # Create StringVars to track password fields
        self.password_var = tk.StringVar()
        self.confirm_var = tk.StringVar()
        
        self.user_entry = self._entry(self.form_frame, "Choose a username")
        
        # Password entry with variable binding
        self.pass_entry = self._entry(self.form_frame, "Password", show="•", textvariable=self.password_var)
        
        self.pass2_entry = self._entry(self.form_frame, "Confirm password", show="•", textvariable=self.confirm_var)
        self.pass2_entry.bind("<Return>", lambda e: self._do_register())
        
        # Create password strength checker
        if hasattr(self, 'password_checker') and self.password_checker:
            self.password_checker.checker_frame.destroy()
        
        self.password_checker = PasswordStrengthChecker(
            self.form_frame, self.password_var, self.confirm_var
        )
        
        # Create submit button
        self.register_button = make_button(
            self.form_frame, "CREATE ACCOUNT", self._do_register
        )
        self.register_button.pack(fill="x", pady=(12, 0), ipady=4)
        
        # Bind confirm password to validate button state
        self.confirm_var.trace_add("write", lambda *args: self._update_register_button())
        
        # Bind password changes to update button state
        self.password_var.trace_add("write", lambda *args: self._update_register_button())
        
        # Initially set button state based on password
        self._update_register_button()

    def _update_register_button(self):
        """Update register button state based on password strength and confirmation"""
        if hasattr(self, 'password_checker') and self.password_checker and hasattr(self, 'register_button'):
            self.password_checker.update_submit_button(self.register_button)

    def _do_register(self):
        username = self._get_entry(self.user_entry, "Choose a username")
        password = self._get_entry(self.pass_entry, "Password")
        confirm = self._get_entry(self.pass2_entry, "Confirm password")

        if not username or not password:
            self.err_var.set("All fields are required.")
            return

        if password != confirm:
            self.err_var.set("Passwords do not match.")
            return

        # Check password strength (NIST-based)
        if self.password_checker:
            score, is_strong_enough = self.password_checker._on_password_change()
            # Require at least "Fair" (score >= 2) — meets NIST baseline
            if not is_strong_enough:
                self.err_var.set(
                    "Password does not meet NIST guidelines.\n"
                    "Must be at least 8 characters and not a common password.\n"
                    "Consider a longer passphrase."
                )
                return

        # Proceed with registration...
        try:
            result = client.register(username, password)
            self.app.on_login_success(result["username"], result["role"])
        except Exception as e:
            self.err_var.set(str(e))

    def _do_login(self):
        username = self._get_entry(self.user_entry, "Username")
        password = self._get_entry(self.pass_entry, "Password")
        if not username or not password:
            self.err_var.set("Please enter both username and password.")
            return
        try:
            # ── BACKEND TO FIX ──────────────────────────────────────────────
            # client.login() sends credentials over socket and returns:
            # {"username": str, "role": "user"|"moderator"|"admin"}
            result = client.login(username, password)
            # ─────────────────────────────────────────────────────────────
            self.app.on_login_success(result["username"], result["role"])
        except Exception as e:
            self.err_var.set(str(e))
    
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

class MainFrame(tk.Frame):
    """
    The main app layout after login.
    Contains the Sidebar (left) and FeedFrame (right).
    Manages which board is currently selected.
    """
    def __init__(self, master: App):
        super().__init__(master, bg=BG_DARK)
        self.app = master
        self._build()

    def _build(self):
        # ── Top nav bar ─────────────────────────────────────────
        nav = tk.Frame(self, bg=BG_MEDIUM,
                       highlightbackground=BORDER, highlightthickness=1)
        nav.pack(fill="x", side="top")

        tk.Label(nav, text=".toString()", font=("Georgia", 16, "bold"),
                 fg=ACCENT, bg=BG_MEDIUM).pack(side="left", padx=16, pady=10)

        # Admin/Moderator menu button (if admin)
        if self.app.user_role == "admin":
            make_button(nav, "🔧 Admin Panel", self._open_admin_panel,
                        bg=DANGER, fg=TEXT_PRI, padx=10, pady=4).pack(side="left", padx=8, pady=8)

        # User info + logout (right side of nav)
        tk.Label(nav, text=f"👤 {self.app.current_user}  [{self.app.user_role}]",
                 font=FONT_SMALL, fg=TEXT_SEC, bg=BG_MEDIUM).pack(side="right", padx=8)
        make_button(nav, "Log Out", self.app.logout,
                    bg=BG_LIGHT, fg=TEXT_SEC, padx=10, pady=4).pack(side="right", padx=8, pady=8)

        # ── Body: sidebar + feed ─────────────────────────────────
        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        # Sidebar (fixed width)
        self.sidebar = Sidebar(body, app=self.app, on_board_select=self._on_board_selected)
        self.sidebar.pack(side="left", fill="y")

        # Vertical separator
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # Feed area (expands to fill remaining space)
        self.feed_frame = FeedFrame(body, app=self.app)
        self.feed_frame.pack(side="left", fill="both", expand=True)

        # Show home feed on startup
        self._on_board_selected(None)

    def _on_board_selected(self, board: dict):
        """
        Called by Sidebar when user clicks a board.
        board=None means "Home" (all subscribed boards).
        """
        self.feed_frame.show_feed(board)

    def _open_admin_panel(self):
        """Open the admin control panel for managing moderators and viewing audit logs."""
        AdminPanel(self.app).show()

class Sidebar(tk.Frame):
    """
    Left navigation panel.
    Shows: Home, subscribed boards, all boards (discover), create board.
    """
    def __init__(self, master, app: App, on_board_select):
        super().__init__(master, bg=BG_MEDIUM, width=240)
        self.pack_propagate(False)
        self.app             = app
        self.on_board_select = on_board_select
        self._build()

    def _build(self):
        # Scrollable inner frame
        canvas = tk.Canvas(self, bg=BG_MEDIUM, bd=0, highlightthickness=0, width=240)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = tk.Frame(canvas, bg=BG_MEDIUM)

        self.inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner, anchor="nw", width=240)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._populate()

    def _populate(self):
        """(Re)build the sidebar content. Call after subscribe/unsubscribe."""
        for w in self.inner.winfo_children():
            w.destroy()

        pad = {"padx": 16, "pady": 3}

        # ── Home ────────────────────────────────────────────────
        self._section_label("FEEDS")
        self._nav_btn("🏠  Home", lambda: self.on_board_select(None))

        tk.Frame(self.inner, bg=BORDER, height=1).pack(fill="x", **pad)

        # ── My Boards (subscribed) ───────────────────────────────
        self._section_label("MY BOARDS")
        # ── BACKEND TO FIX ─────────────────────────────────────────
        # client.get_subscribed_boards() returns list of board dicts
        subs = client.get_subscribed_boards(self.app.current_user)
        # ─────────────────────────────────────────────────────────
        if subs:
            for board in subs:
                self._board_btn(board)
        else:
            make_label(self.inner, "Not subscribed to any boards.",
                       font=FONT_SMALL, fg=TEXT_MUTED).pack(**pad, anchor="w")

        tk.Frame(self.inner, bg=BORDER, height=1).pack(fill="x", **pad)

        # ── Discover All Boards ──────────────────────────────────
        self._section_label("DISCOVER")
        # ── BACKEND TO FIX ─────────────────────────────────────────
        # client.get_all_boards() returns complete list of board dicts
        all_boards = client.get_all_boards()
        # ─────────────────────────────────────────────────────────
        sub_ids = {b["id"] for b in subs}
        for board in all_boards:
            if board["id"] not in sub_ids:
                self._discover_board_btn(board)

        tk.Frame(self.inner, bg=BORDER, height=1).pack(fill="x", **pad)

        # ── Create Board ─────────────────────────────────────────
        self._section_label("CREATE")
        make_button(self.inner, "+ New Board", self._open_create_board,
                    bg=ACCENT, pady=6).pack(fill="x", padx=16, pady=4)

    def _section_label(self, text: str):
        make_label(self.inner, text, font=("Helvetica", 9, "bold"),
                   fg=TEXT_MUTED).pack(anchor="w", padx=16, pady=(10, 2))

    def _nav_btn(self, text: str, command):
        btn = tk.Button(self.inner, text=text, font=FONT_BODY,
                        bg=BG_MEDIUM, fg=TEXT_PRI, activebackground=BG_LIGHT,
                        relief="flat", anchor="w", cursor="hand2",
                        command=command, bd=0)
        btn.pack(fill="x", padx=8, pady=1, ipady=4)
        btn.bind("<Enter>", lambda e: btn.config(bg=BG_LIGHT))
        btn.bind("<Leave>", lambda e: btn.config(bg=BG_MEDIUM))

    def _board_btn(self, board: dict):
        """Clickable subscribed board button in sidebar."""
        row = tk.Frame(self.inner, bg=BG_MEDIUM)
        row.pack(fill="x", padx=8, pady=1)

        btn = tk.Button(row,
                        text=f"  {board['name']}",
                        font=FONT_BODY, bg=BG_MEDIUM, fg=TEXT_PRI,
                        activebackground=BG_LIGHT, relief="flat",
                        anchor="w", cursor="hand2", bd=0,
                        command=lambda b=board: self.on_board_select(b))
        btn.pack(side="left", fill="x", expand=True, ipady=3)
        btn.bind("<Enter>", lambda e: btn.config(bg=BG_LIGHT))
        btn.bind("<Leave>", lambda e: btn.config(bg=BG_MEDIUM))

    def _discover_board_btn(self, board: dict):
        """Board not yet subscribed — shown in Discover section with Join button."""
        row = tk.Frame(self.inner, bg=BG_MEDIUM)
        row.pack(fill="x", padx=8, pady=1)

        tk.Label(row, text=f"  {board['name']}", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=BG_MEDIUM, anchor="w").pack(side="left", fill="x", expand=True)

        def join(b=board):
            try:
                # ── BACKEND TO FIX ──────────────────────────────────
                # client.subscribe_board() sends SUBSCRIBE request to server
                client.subscribe_board(self.app.current_user, b["id"])
                # ──────────────────────────────────────────────────
                self._populate()
                self.on_board_select(b)
            except Exception as e:
                messagebox.showerror("Error", str(e))

        make_button(row, "Join", join, bg=SUCCESS, pady=2, padx=6,
                    font=FONT_SMALL).pack(side="right", padx=4, pady=2)

    def _open_create_board(self):
        """Popup dialog to create a new board."""
        win = tk.Toplevel(self, bg=BG_MEDIUM)
        win.title("Create Board")
        win.geometry("380x260")
        win.resizable(False, False)
        win.grab_set()

        make_label(win, "Create a New Board", font=FONT_BOARD).pack(pady=(20, 4))
        make_label(win, "Name (will add r/ prefix)", font=FONT_SMALL, fg=TEXT_SEC).pack(anchor="w", padx=24)
        name_e = tk.Entry(win, font=FONT_INPUT, bg=BG_LIGHT, fg=TEXT_PRI,
                          insertbackground=TEXT_PRI, relief="flat")
        name_e.pack(fill="x", padx=24, ipady=7, pady=4)

        make_label(win, "Description", font=FONT_SMALL, fg=TEXT_SEC).pack(anchor="w", padx=24)
        desc_e = tk.Entry(win, font=FONT_INPUT, bg=BG_LIGHT, fg=TEXT_PRI,
                          insertbackground=TEXT_PRI, relief="flat")
        desc_e.pack(fill="x", padx=24, ipady=7, pady=4)

        err_lbl = make_label(win, "", font=FONT_SMALL, fg=DANGER)
        err_lbl.pack()

        def submit():
            name = name_e.get().strip()
            desc = desc_e.get().strip()
            if not name:
                err_lbl.config(text="Board name is required.")
                return
            if not desc:
                err_lbl.config(text="Description is required.")
                return
            try:
                # ── BACKEND TO FIX ──────────────────────────────────
                # client.create_board() sends CREATE_BOARD to server
                new_board = client.create_board(self.app.current_user, name, desc)
                # ──────────────────────────────────────────────────
                win.destroy()
                self._populate()
                self.on_board_select(new_board)
            except Exception as e:
                err_lbl.config(text=str(e))

        make_button(win, "CREATE BOARD", submit).pack(pady=8, ipadx=10)

    def refresh(self):
        """Public method — call this to force sidebar to reload board list."""
        self._populate()


# ═══════════════════════════════════════════════════════════════
#  FeedFrame — Right panel: feed list or post detail
# ═══════════════════════════════════════════════════════════════
class FeedFrame(tk.Frame):
    """
    Right-side content area.
    Switches between:
      - FeedView: grid of post cards for a board (or home)
      - PostView: single post expanded with comments
    """
    def __init__(self, master, app: App):
        super().__init__(master, bg=BG_DARK)
        self.app          = app
        self.current_board = None  # currently selected board dict

    def show_feed(self, board: dict):
        """Display the feed for a given board (or home if board=None)."""
        self.current_board = board
        for w in self.winfo_children():
            w.destroy()
        FeedView(self, app=self.app, board=board,
                 on_post_click=self._open_post).pack(fill="both", expand=True)

    def _open_post(self, message: dict, board: dict):
        """Open a post's detail view with comments."""
        for w in self.winfo_children():
            w.destroy()
        PostView(self, app=self.app, message=message, board=board,
                 on_back=lambda: self.show_feed(self.current_board)).pack(fill="both", expand=True)


# ═══════════════════════════════════════════════════════════════
#  FeedView — Scrollable list of posts for a board
# ═══════════════════════════════════════════════════════════════
class FeedView(tk.Frame):
    """
    Shows all posts for a selected board, or the home feed (all subscribed boards).
    Each post is rendered as a PostCard widget.
    """
    def __init__(self, master, app: App, board: dict, on_post_click):
        super().__init__(master, bg=BG_DARK)
        self.app          = app
        self.board        = board
        self.on_post_click = on_post_click
        self._build()

    def _build(self):
        # ── Header ───────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_DARK)
        header.pack(fill="x", padx=24, pady=(18, 0))

        if self.board:
            # Single board view
            title_text = self.board["name"]
            sub_text   = self.board.get("description", "")
            tk.Label(header, text=title_text, font=FONT_TITLE,
                     fg=TEXT_PRI, bg=BG_DARK).pack(anchor="w")
            tk.Label(header, text=sub_text, font=FONT_META,
                     fg=TEXT_SEC, bg=BG_DARK).pack(anchor="w")

            # Subscribe / Unsubscribe toggle
            # ── BACKEND TO FIX ──────────────────────────────────────
            subs = client.get_subscribed_boards(self.app.current_user)
            # ──────────────────────────────────────────────────────
            sub_ids  = {b["id"] for b in subs}
            is_subbed = self.board["id"] in sub_ids

            if is_subbed:
                make_button(header, "✓ Joined", self._unsubscribe,
                            bg=BG_LIGHT, fg=TEXT_SEC, pady=4).pack(side="right", pady=4)
            else:
                make_button(header, "Join", self._subscribe,
                            bg=SUCCESS, pady=4).pack(side="right", pady=4)
        else:
            # Home feed
            tk.Label(header, text="Home", font=FONT_TITLE,
                     fg=TEXT_PRI, bg=BG_DARK).pack(anchor="w")
            tk.Label(header, text="Posts from boards you've joined",
                     font=FONT_META, fg=TEXT_SEC, bg=BG_DARK).pack(anchor="w")

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=24, pady=10)

        # ── New Post box (if subscribed) ─────────────────────────
        if self.board:
            # ── BACKEND TO FIX ──────────────────────────────────────
            subs = client.get_subscribed_boards(self.app.current_user)
            # ──────────────────────────────────────────────────────
            if self.board["id"] in {b["id"] for b in subs}:
                self._build_compose_box()

        # ── Scrollable post list ──────────────────────────────────
        container = tk.Frame(self, bg=BG_DARK)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg=BG_DARK, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=BG_DARK)

        self.scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mouse-wheel scrolling
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._load_posts()

    def _build_compose_box(self):
        """Quick post composer shown at top of board feed."""
        box = tk.Frame(self, bg=BG_MEDIUM,
                       highlightbackground=BORDER, highlightthickness=1)
        box.pack(fill="x", padx=24, pady=(0, 8))

        make_label(box, "Create a Post", font=FONT_BODY, fg=TEXT_SEC).pack(
            anchor="w", padx=12, pady=(8, 4))

        self.compose_entry = tk.Text(box, font=FONT_INPUT, bg=BG_LIGHT, fg=TEXT_PRI,
                                     insertbackground=TEXT_PRI, relief="flat",
                                     height=3, wrap="word")
        self.compose_entry.pack(fill="x", padx=12, pady=4)

        err_var = tk.StringVar()
        tk.Label(box, textvariable=err_var, font=FONT_SMALL,
                 fg=DANGER, bg=BG_MEDIUM).pack(anchor="w", padx=12)

        def post():
            content = self.compose_entry.get("1.0", "end").strip()
            if not content:
                err_var.set("Message cannot be empty.")
                return
            try:
                # ── BACKEND TO FIX ──────────────────────────────────
                # client.post_message() sends POST_MESSAGE to server
                client.post_message(self.app.current_user, self.board["id"], content)
                # ──────────────────────────────────────────────────
                self.compose_entry.delete("1.0", "end")
                err_var.set("")
                self._load_posts()   # Refresh feed
            except Exception as e:
                err_var.set(str(e))

        make_button(box, "Post", post, pady=4).pack(anchor="e", padx=12, pady=(0, 8))

    def _load_posts(self):
        """Fetch and render posts. Called on init and after posting."""
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        if self.board:
            boards_to_show = [self.board]
        else:
            # Home: aggregate all subscribed boards
            # ── BACKEND TO FIX ──────────────────────────────────────
            boards_to_show = client.get_subscribed_boards(self.app.current_user)
            

        all_msgs = []
        for b in boards_to_show:
            # ── BACKEND TO FIX ──────────────────────────────────────
            # client.get_messages() returns list of message dicts for a board
            msgs = client.get_messages(b["id"])
            
            for m in msgs:
                all_msgs.append((m, b))

        if not all_msgs:
            make_label(self.scroll_frame,
                       "No posts yet. Be the first to post!",
                       font=FONT_BODY, fg=TEXT_SEC, bg=BG_DARK).pack(pady=40)
            return

        for msg, board in all_msgs:
            PostCard(
                self.scroll_frame,
                app=self.app,
                message=msg,
                board=board,
                on_click=lambda m=msg, b=board: self.on_post_click(m, b),
                on_refresh=self._load_posts,
            ).pack(fill="x", padx=24, pady=6)

    def _subscribe(self):
        try:
            client.subscribe_board(self.app.current_user, self.board["id"])
            self._build()  # Refresh view to show unsubscribe button
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _unsubscribe(self):
        try:
            client.unsubscribe_board(self.app.current_user, self.board["id"])
            self._build()
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ═══════════════════════════════════════════════════════════════
#  PostCard — Single post preview card in the feed
# ═══════════════════════════════════════════════════════════════
class PostCard(tk.Frame):
    """
    Compact post card shown in the feed.
    Displays: board name (home), author, timestamp, content preview,
    comment count, edit/delete actions.
    Clicking opens PostView.
    """
    def __init__(self, master, app: App, message: dict, board: dict,
                 on_click, on_refresh):
        super().__init__(master, bg=BG_MEDIUM, cursor="hand2",
                         highlightbackground=BORDER, highlightthickness=1)
        self.app        = app
        self.message    = message
        self.board      = board
        self.on_click   = on_click
        self.on_refresh = on_refresh
        self._build()
        # Clicking anywhere on the card opens the post
        self.bind("<Button-1>", lambda e: on_click())

    def _build(self):
        # ── Meta row ─────────────────────────────────────────────
        meta = tk.Frame(self, bg=BG_MEDIUM)
        meta.pack(fill="x", padx=14, pady=(10, 4))

        # Board name (shown on home feed)
        tk.Label(meta,
                 text=f"{self.board['name']}",
                 font=("Helvetica", 9, "bold"),
                 fg=ACCENT, bg=BG_MEDIUM).pack(side="left")

        tk.Label(meta, text="  •  ", font=FONT_SMALL,
                 fg=TEXT_MUTED, bg=BG_MEDIUM).pack(side="left")
        tk.Label(meta,
                 text=f"Posted by u/{self.message['author']}  {self.message['timestamp']}",
                 font=FONT_META, fg=TEXT_SEC, bg=BG_MEDIUM).pack(side="left")

        # ── Content preview ──────────────────────────────────────
        content = self.message["content"]
        preview = (content[:180] + "…") if len(content) > 180 else content
        tk.Label(self, text=preview, font=FONT_BODY, fg=TEXT_PRI,
                 bg=BG_MEDIUM, wraplength=700, justify="left",
                 anchor="w").pack(fill="x", padx=14, pady=(0, 8))

        # ── Action row ───────────────────────────────────────────
        actions = tk.Frame(self, bg=BG_MEDIUM)
        actions.pack(fill="x", padx=10, pady=(0, 8))

        comment_count = len(self.message.get("comments", []))
        tk.Button(actions,
                  text=f"💬  {comment_count} comment{'s' if comment_count != 1 else ''}",
                  font=FONT_SMALL, bg=BG_MEDIUM, fg=TEXT_SEC,
                  activebackground=BG_LIGHT, relief="flat", cursor="hand2",
                  command=self.on_click, bd=0).pack(side="left", padx=4)

        # Edit — only shown to the post author
        if self.message["author"] == self.app.current_user:
            tk.Button(actions, text="✏ Edit",
                      font=FONT_SMALL, bg=BG_MEDIUM, fg=TEXT_SEC,
                      activebackground=BG_LIGHT, relief="flat", cursor="hand2",
                      command=self._edit, bd=0).pack(side="left", padx=4)

        # Delete — shown to author OR moderator/admin
        if (self.message["author"] == self.app.current_user or
                self.app.user_role in ("moderator", "admin")):
            tk.Button(actions, text="🗑 Delete",
                      font=FONT_SMALL, bg=BG_MEDIUM, fg=DANGER,
                      activebackground=BG_LIGHT, relief="flat", cursor="hand2",
                      command=self._delete, bd=0).pack(side="left", padx=4)

    def _edit(self):
        """Inline edit dialog for the post content."""
        win = tk.Toplevel(self, bg=BG_MEDIUM)
        win.title("Edit Post")
        win.geometry("500x240")
        win.grab_set()

        make_label(win, "Edit your post:", font=FONT_BOARD).pack(pady=(16, 8))
        text_w = tk.Text(win, font=FONT_INPUT, bg=BG_LIGHT, fg=TEXT_PRI,
                         insertbackground=TEXT_PRI, relief="flat", height=5, wrap="word")
        text_w.insert("1.0", self.message["content"].replace(" (edited)", ""))
        text_w.pack(fill="x", padx=20, pady=4)

        err_lbl = make_label(win, "", font=FONT_SMALL, fg=DANGER)
        err_lbl.pack()

        def save():
            new_content = text_w.get("1.0", "end").strip()
            if not new_content:
                err_lbl.config(text="Content cannot be empty.")
                return
            try:
                # ── BACKEND TO FIX ──────────────────────────────────
                # client.edit_message() sends EDIT_MESSAGE request to server
                client.edit_message(self.app.current_user, self.message["id"], new_content)
                
                win.destroy()
                self.on_refresh()
            except Exception as e:
                err_lbl.config(text=str(e))

        make_button(win, "Save Changes", save).pack(pady=8)

    def _delete(self):
        if not messagebox.askyesno("Delete Post", "Are you sure you want to delete this post?"):
            return
        try:
            # ── BACKEND TO FIX ──────────────────────────────────────
            # client.delete_message() sends DELETE_MESSAGE to server
            # Server enforces: only author or moderator/admin can delete
            client.delete_message(self.app.current_user,
                                  self.message["id"],
                                  self.app.user_role)
            
            self.on_refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))


class PostView(tk.Frame):
    """
    Full-page view of a single post.
    Shows: full post content, edit/delete, comment list, comment composer.
    """
    def __init__(self, master, app: App, message: dict, board: dict, on_back):
        super().__init__(master, bg=BG_DARK)
        self.app     = app
        self.message = message
        self.board   = board
        self.on_back = on_back
        self._build()

    def _build(self):
        # Scrollable outer container
        canvas = tk.Canvas(self, bg=BG_DARK, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = tk.Frame(canvas, bg=BG_DARK)

        self.inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Back button 
        make_button(self.inner, "← Back", self.on_back,
                    bg=BG_LIGHT, fg=TEXT_SEC, pady=4).pack(
                    anchor="w", padx=24, pady=(16, 0))

        # Post card 
        post_frame = tk.Frame(self.inner, bg=BG_MEDIUM,
                              highlightbackground=BORDER, highlightthickness=1)
        post_frame.pack(fill="x", padx=24, pady=12)

        # Board + author meta
        meta = tk.Frame(post_frame, bg=BG_MEDIUM)
        meta.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(meta, text=self.board["name"],
                 font=("Helvetica", 9, "bold"), fg=ACCENT,
                 bg=BG_MEDIUM).pack(side="left")
        tk.Label(meta, text=f"  •  Posted by u/{self.message['author']}  {self.message['timestamp']}",
                 font=FONT_META, fg=TEXT_SEC, bg=BG_MEDIUM).pack(side="left")

        # Full content
        tk.Label(post_frame, text=self.message["content"],
                 font=FONT_BODY, fg=TEXT_PRI, bg=BG_MEDIUM,
                 wraplength=760, justify="left", anchor="w").pack(
                 fill="x", padx=14, pady=(0, 12))

        # Edit/delete actions
        actions = tk.Frame(post_frame, bg=BG_MEDIUM)
        actions.pack(fill="x", padx=10, pady=(0, 10))

        if self.message["author"] == self.app.current_user:
            make_button(actions, "✏ Edit", self._edit_post,
                        bg=BG_LIGHT, fg=TEXT_SEC, pady=3, padx=8,
                        font=FONT_SMALL).pack(side="left", padx=4)

        if (self.message["author"] == self.app.current_user or
                self.app.user_role in ("moderator", "admin")):
            make_button(actions, "🗑 Delete", self._delete_post,
                        bg=DANGER, fg=TEXT_PRI, pady=3, padx=8,
                        font=FONT_SMALL).pack(side="left", padx=4)

        # Comment composer 
        tk.Frame(self.inner, bg=BORDER, height=1).pack(fill="x", padx=24)
        comment_header = tk.Frame(self.inner, bg=BG_DARK)
        comment_header.pack(fill="x", padx=24, pady=(12, 4))
        tk.Label(comment_header,
                 text=f"Comments ({len(self.message.get('comments', []))})",
                 font=FONT_BOARD, fg=TEXT_PRI, bg=BG_DARK).pack(side="left")

        # Comment input
        compose = tk.Frame(self.inner, bg=BG_MEDIUM,
                           highlightbackground=BORDER, highlightthickness=1)
        compose.pack(fill="x", padx=24, pady=(0, 10))

        self.comment_entry = tk.Text(compose, font=FONT_INPUT, bg=BG_LIGHT,
                                     fg=TEXT_PRI, insertbackground=TEXT_PRI,
                                     relief="flat", height=3, wrap="word")
        self.comment_entry.pack(fill="x", padx=12, pady=(10, 4))

        self.comment_err = tk.StringVar()
        tk.Label(compose, textvariable=self.comment_err, font=FONT_SMALL,
                 fg=DANGER, bg=BG_MEDIUM).pack(anchor="w", padx=12)
        make_button(compose, "Comment", self._post_comment, pady=4).pack(
                    anchor="e", padx=12, pady=(0, 8))

        # Comment list
        self.comments_frame = tk.Frame(self.inner, bg=BG_DARK)
        self.comments_frame.pack(fill="x", padx=24)
        self._render_comments()

    def _render_comments(self):
        """Re-render the comment list (called after new comment posted)."""
        for w in self.comments_frame.winfo_children():
            w.destroy()

        comments = self.message.get("comments", [])
        if not comments:
            make_label(self.comments_frame,
                       "No comments yet. Share your thoughts!",
                       font=FONT_BODY, fg=TEXT_SEC, bg=BG_DARK).pack(pady=16)
            return

        for comment in comments:
            CommentCard(self.comments_frame, app=self.app, comment=comment,
                        message=self.message).pack(fill="x", pady=3)

    def _post_comment(self):
        content = self.comment_entry.get("1.0", "end").strip()
        if not content:
            self.comment_err.set("Comment cannot be empty.")
            return
        try:
            # ── BACKEND TO FIX ──────────────────────────────────────
            # client.post_comment() sends POST_COMMENT request to server
            new_comment = client.post_comment(
                self.app.current_user, self.message["id"], content)
            
            self.message["comments"].append(new_comment)
            self.comment_entry.delete("1.0", "end")
            self.comment_err.set("")
            self._render_comments()
        except Exception as e:
            self.comment_err.set(str(e))

    def _edit_post(self):
        win = tk.Toplevel(self, bg=BG_MEDIUM)
        win.title("Edit Post")
        win.geometry("500x240")
        win.grab_set()

        make_label(win, "Edit your post:", font=FONT_BOARD).pack(pady=(16, 8))
        text_w = tk.Text(win, font=FONT_INPUT, bg=BG_LIGHT, fg=TEXT_PRI,
                         insertbackground=TEXT_PRI, relief="flat", height=5, wrap="word")
        text_w.insert("1.0", self.message["content"].replace(" (edited)", ""))
        text_w.pack(fill="x", padx=20, pady=4)

        err_lbl = make_label(win, "", font=FONT_SMALL, fg=DANGER)
        err_lbl.pack()

        def save():
            new_content = text_w.get("1.0", "end").strip()
            if not new_content:
                err_lbl.config(text="Content cannot be empty.")
                return
            try:
                client.edit_message(self.app.current_user,
                                    self.message["id"], new_content)
                self.message["content"] = new_content + " (edited)"
                win.destroy()
                # Rebuild this view to reflect changes
                for w in self.winfo_children():
                    w.destroy()
                self._build()
            except Exception as e:
                err_lbl.config(text=str(e))

        make_button(win, "Save Changes", save).pack(pady=8)

    def _delete_post(self):
        if not messagebox.askyesno("Delete Post", "Delete this post and all its comments?"):
            return
        try:
            client.delete_message(self.app.current_user,
                                  self.message["id"],
                                  self.app.user_role)
            self.on_back()
        except Exception as e:
            messagebox.showerror("Error", str(e))



class CommentCard(tk.Frame):
    """
    Renders one comment.
    Shows author, timestamp, content.
    No delete for comments yet, we can implement later if desired.
    """
    def __init__(self, master, app: App, comment: dict, message: dict):
        super().__init__(master, bg=BG_MEDIUM,
                         highlightbackground=BORDER, highlightthickness=1)
        self.app     = app
        self.comment = comment
        self.message = message
        self._build()

    def _build(self):
        meta = tk.Frame(self, bg=BG_MEDIUM)
        meta.pack(fill="x", padx=12, pady=(8, 2))

        tk.Label(meta, text=f"u/{self.comment['author']}",
                 font=("Helvetica", 9, "bold"), fg=ACCENT,
                 bg=BG_MEDIUM).pack(side="left")
        tk.Label(meta, text=f"  {self.comment['timestamp']}",
                 font=FONT_META, fg=TEXT_SEC, bg=BG_MEDIUM).pack(side="left")

        tk.Label(self, text=self.comment["content"],
                 font=FONT_BODY, fg=TEXT_PRI, bg=BG_MEDIUM,
                 wraplength=740, justify="left", anchor="w").pack(
                 fill="x", padx=12, pady=(2, 10))


class AdminPanel(tk.Toplevel):
    """
    Admin control panel for managing moderators and viewing audit logs.
    Provides interface for upgrading/downgrading users and assigning board moderators.
    """
    def __init__(self, app: App):
        super().__init__(app)
        self.app = app
        self.title("Admin Panel - .toString()")
        self.geometry("800x600")
        self.configure(bg=BG_DARK)
        self._build()

    def _build(self):
        """Build the admin panel interface."""
        # Title
        tk.Label(self, text="🔧 Admin Panel", font=FONT_TITLE,
                 fg=ACCENT, bg=BG_DARK).pack(pady=16, padx=16)

        # Tabs for different admin functions
        tab_frame = tk.Frame(self, bg=BG_MEDIUM)
        tab_frame.pack(fill="both", expand=True, padx=16, pady=0)

        notebook = ttk.Notebook(tab_frame)
        notebook.pack(fill="both", expand=True)

        # Tab 1: Promote/Demote Users
        promote_frame = tk.Frame(notebook, bg=BG_MEDIUM)
        notebook.add(promote_frame, text="Promote to Moderator")
        self._build_promote_tab(promote_frame)

        # Tab 2: Manage Board Moderators
        board_mod_frame = tk.Frame(notebook, bg=BG_MEDIUM)
        notebook.add(board_mod_frame, text="Board Moderators")
        self._build_board_moderators_tab(board_mod_frame)

        # Tab 3: Audit Logs
        logs_frame = tk.Frame(notebook, bg=BG_MEDIUM)
        notebook.add(logs_frame, text="Audit Logs")
        self._build_audit_logs_tab(logs_frame)

    def _build_promote_tab(self, parent):
        """Build tab for promoting/demoting users to/from moderator."""
        # Title
        tk.Label(parent, text="System Moderator Management",
                 font=FONT_BOARD, fg=ACCENT, bg=BG_MEDIUM).pack(pady=12, padx=12, anchor="w")

        # Input frame
        input_frame = tk.Frame(parent, bg=BG_MEDIUM)
        input_frame.pack(fill="x", padx=12, pady=8)

        tk.Label(input_frame, text="Username:", font=FONT_BODY,
                 fg=TEXT_PRI, bg=BG_MEDIUM).pack(side="left", padx=4)
        self.promote_username_var = tk.StringVar()
        entry = tk.Entry(input_frame, textvariable=self.promote_username_var,
                         font=FONT_BODY, bg=BG_LIGHT, fg=TEXT_PRI, relief="flat", width=20)
        entry.pack(side="left", padx=4)

        make_button(input_frame, "Promote to Moderator",
                    self._do_promote_user, bg=SUCCESS).pack(side="left", padx=4)
        make_button(input_frame, "Downgrade to User",
                    self._do_downgrade_user, bg=DANGER).pack(side="left", padx=4)

        # Status label
        self.promote_status_var = tk.StringVar()
        tk.Label(parent, textvariable=self.promote_status_var, font=FONT_SMALL,
                 fg=TEXT_SEC, bg=BG_MEDIUM).pack(pady=8)

    def _build_board_moderators_tab(self, parent):
        """Build tab for assigning board moderators."""
        tk.Label(parent, text="Assign Board Moderators",
                 font=FONT_BOARD, fg=ACCENT, bg=BG_MEDIUM).pack(pady=12, padx=12, anchor="w")

        # Input frame
        input_frame = tk.Frame(parent, bg=BG_MEDIUM)
        input_frame.pack(fill="x", padx=12, pady=8)

        tk.Label(input_frame, text="Username:", font=FONT_BODY,
                 fg=TEXT_PRI, bg=BG_MEDIUM).pack(side="left", padx=4)
        self.board_mod_username_var = tk.StringVar()
        entry1 = tk.Entry(input_frame, textvariable=self.board_mod_username_var,
                          font=FONT_BODY, bg=BG_LIGHT, fg=TEXT_PRI, relief="flat", width=15)
        entry1.pack(side="left", padx=4)

        tk.Label(input_frame, text="Board ID:", font=FONT_BODY,
                 fg=TEXT_PRI, bg=BG_MEDIUM).pack(side="left", padx=4)
        self.board_mod_board_id_var = tk.StringVar()
        entry2 = tk.Entry(input_frame, textvariable=self.board_mod_board_id_var,
                          font=FONT_BODY, bg=BG_LIGHT, fg=TEXT_PRI, relief="flat", width=10)
        entry2.pack(side="left", padx=4)

        make_button(input_frame, "Assign", self._do_assign_board_mod, bg=SUCCESS).pack(side="left", padx=4)
        make_button(input_frame, "Remove", self._do_remove_board_mod, bg=DANGER).pack(side="left", padx=4)

        # Status label
        self.board_mod_status_var = tk.StringVar()
        tk.Label(parent, textvariable=self.board_mod_status_var, font=FONT_SMALL,
                 fg=TEXT_SEC, bg=BG_MEDIUM).pack(pady=8)

        # Board moderators list
        tk.Label(parent, text="Moderators by Board:", font=FONT_BODY,
                 fg=TEXT_PRI, bg=BG_MEDIUM).pack(pady=(12, 4), padx=12, anchor="w")

        # Scrollable text area for board moderators
        scroll_frame = tk.Frame(parent, bg=BG_MEDIUM)
        scroll_frame.pack(fill="both", expand=True, padx=12, pady=8)

        scrollbar = tk.Scrollbar(scroll_frame)
        scrollbar.pack(side="right", fill="y")

        self.board_mods_text = scrolledtext.ScrolledText(
            scroll_frame, font=FONT_SMALL, bg=BG_LIGHT, fg=TEXT_PRI,
            yscrollcommand=scrollbar.set, relief="flat", height=10, width=80
        )
        self.board_mods_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.board_mods_text.yview)

        # Refresh button
        make_button(parent, "Refresh Board Moderators List",
                    self._refresh_board_mods, bg=ACCENT).pack(pady=8)

        # Initial load
        self._refresh_board_mods()

    def _build_audit_logs_tab(self, parent):
        """Build tab for viewing audit logs."""
        tk.Label(parent, text="Audit Logs",
                 font=FONT_BOARD, fg=ACCENT, bg=BG_MEDIUM).pack(pady=12, padx=12, anchor="w")

        # Controls
        controls_frame = tk.Frame(parent, bg=BG_MEDIUM)
        controls_frame.pack(fill="x", padx=12, pady=8)

        tk.Label(controls_frame, text="Limit:", font=FONT_BODY,
                 fg=TEXT_PRI, bg=BG_MEDIUM).pack(side="left", padx=4)
        self.audit_limit_var = tk.StringVar(value="50")
        entry = tk.Entry(controls_frame, textvariable=self.audit_limit_var,
                         font=FONT_BODY, bg=BG_LIGHT, fg=TEXT_PRI, relief="flat", width=5)
        entry.pack(side="left", padx=4)

        make_button(controls_frame, "Load Audit Logs",
                    self._load_audit_logs, bg=ACCENT).pack(side="left", padx=4)

        # Scrollable text area for audit logs
        scroll_frame = tk.Frame(parent, bg=BG_MEDIUM)
        scroll_frame.pack(fill="both", expand=True, padx=12, pady=8)

        scrollbar = tk.Scrollbar(scroll_frame)
        scrollbar.pack(side="right", fill="y")

        self.audit_logs_text = scrolledtext.ScrolledText(
            scroll_frame, font=FONT_SMALL, bg=BG_LIGHT, fg=TEXT_PRI,
            yscrollcommand=scrollbar.set, relief="flat", height=15, width=80
        )
        self.audit_logs_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.audit_logs_text.yview)

        # Initial load
        self._load_audit_logs()

    def _do_promote_user(self):
        """Promote a user to system-wide moderator."""
        username = self.promote_username_var.get()
        if not username:
            self.promote_status_var.set("Error: Please enter a username")
            return
        
        try:
            response = client.upgrade_user(self.app.current_user, username)
            self.promote_status_var.set(f"✓ {response.get('message', 'Success')}")
            self.promote_username_var.set("")
        except Exception as e:
            self.promote_status_var.set(f"Error: {str(e)}")

    def _do_downgrade_user(self):
        """Downgrade a moderator back to regular user."""
        username = self.promote_username_var.get()
        if not username:
            self.promote_status_var.set("Error: Please enter a username")
            return
        
        try:
            response = client.downgrade_user(self.app.current_user, username)
            self.promote_status_var.set(f"✓ {response.get('message', 'Success')}")
            self.promote_username_var.set("")
        except Exception as e:
            self.promote_status_var.set(f"Error: {str(e)}")

    def _do_assign_board_mod(self):
        """Assign user as moderator to a board."""
        username = self.board_mod_username_var.get()
        board_id_str = self.board_mod_board_id_var.get()
        
        if not username or not board_id_str:
            self.board_mod_status_var.set("Error: Please enter both username and board ID")
            return
        
        try:
            board_id = int(board_id_str)
            response = client.assign_board_moderator(self.app.current_user, username, board_id)
            self.board_mod_status_var.set(f"✓ {response.get('message', 'Success')}")
            self.board_mod_username_var.set("")
            self.board_mod_board_id_var.set("")
            self._refresh_board_mods()
        except ValueError:
            self.board_mod_status_var.set("Error: Board ID must be a number")
        except Exception as e:
            self.board_mod_status_var.set(f"Error: {str(e)}")

    def _do_remove_board_mod(self):
        """Remove user as moderator from a board."""
        username = self.board_mod_username_var.get()
        board_id_str = self.board_mod_board_id_var.get()
        
        if not username or not board_id_str:
            self.board_mod_status_var.set("Error: Please enter both username and board ID")
            return
        
        try:
            board_id = int(board_id_str)
            response = client.remove_board_moderator(self.app.current_user, username, board_id)
            self.board_mod_status_var.set(f"✓ {response.get('message', 'Success')}")
            self.board_mod_username_var.set("")
            self.board_mod_board_id_var.set("")
            self._refresh_board_mods()
        except ValueError:
            self.board_mod_status_var.set("Error: Board ID must be a number")
        except Exception as e:
            self.board_mod_status_var.set(f"Error: {str(e)}")

    def _refresh_board_mods(self):
        """Refresh the board moderators list."""
        self.board_mods_text.config(state="normal")
        self.board_mods_text.delete("1.0", "end")
        
        try:
            boards = client.get_all_boards()
            for board in boards:
                board_id = board.get("id")
                response = client.list_board_moderators(board_id)
                mods = response.get("moderators", [])
                
                mod_str = ", ".join(mods) if mods else "(no moderators)"
                self.board_mods_text.insert("end", f"📌 {board['name']} (ID: {board_id}): {mod_str}\n")
        except Exception as e:
            self.board_mods_text.insert("end", f"Error loading board moderators: {str(e)}\n")
        
        self.board_mods_text.config(state="disabled")

    def _load_audit_logs(self):
        """Load and display audit logs."""
        self.audit_logs_text.config(state="normal")
        self.audit_logs_text.delete("1.0", "end")
        
        try:
            limit = int(self.audit_limit_var.get())
        except ValueError:
            self.audit_logs_text.insert("end", "Error: Limit must be a number\n")
            self.audit_logs_text.config(state="disabled")
            return
        
        try:
            response = client.get_audit_logs(self.app.current_user, limit)
            logs = response.get("logs", [])
            total = response.get("total_logs", 0)
            
            self.audit_logs_text.insert("end", f"Total logs: {total} | Showing last {min(limit, len(logs))}\n")
            self.audit_logs_text.insert("end", "─" * 78 + "\n\n")
            
            if logs:
                for log in reversed(logs):  # Show newest first
                    timestamp = log.get("timestamp", "N/A")
                    action = log.get("action", "UNKNOWN")
                    performed_by = log.get("performed_by", "system")
                    target = log.get("target_user", "N/A")
                    board = log.get("board_id", "N/A")
                    details = log.get("details", "")
                    
                    self.audit_logs_text.insert("end", f"[{timestamp}] {action}\n")
                    self.audit_logs_text.insert("end", f"  By: {performed_by} | Target: {target} | Board: {board}\n")
                    if details:
                        self.audit_logs_text.insert("end", f"  Details: {details}\n")
                    self.audit_logs_text.insert("end", "\n")
            else:
                self.audit_logs_text.insert("end", "No audit logs found.\n")
        except Exception as e:
            self.audit_logs_text.insert("end", f"Error loading audit logs: {str(e)}\n")
        
        self.audit_logs_text.config(state="disabled")

    def show(self):
        """Display the admin panel."""
        self.deiconify()
        self.lift()
        self.focus()

if __name__ == "__main__":
    app = App()
    app.mainloop()