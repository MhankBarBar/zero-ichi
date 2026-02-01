"""
Shared session state for the bot.
Used to pass information like QR codes between the bot and the dashboard.
"""


class SessionState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.qr_code: str | None = None
        self.pair_code: str | None = None
        self.phone_number: str | None = None
        self.is_pairing: bool = False
        self.login_error: str | None = None
        self.is_logged_in: bool = False
        self._initialized = True


session_state = SessionState()
