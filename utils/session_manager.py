from datetime import datetime, timedelta

class SessionManager:
    def __init__(self, session_timeout_minutes: int = 60):
        self.last_session_time = None
        self.timeout = timedelta(minutes=session_timeout_minutes)

    def mark_session_start(self):
        """Merkt sich den aktuellen Zeitpunkt als Session-Start."""
        self.last_session_time = datetime.now()

    def is_session_valid(self) -> bool:
        """Gibt True zurück, wenn die letzte Session noch gültig ist."""
        if self.last_session_time is None:
            return False
        return datetime.now() - self.last_session_time < self.timeout