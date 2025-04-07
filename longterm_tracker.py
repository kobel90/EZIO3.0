import json
import os

STATUS_FILE = "longterm_status.json"

class LongtermTracker:
    def __init__(self):
        self.status = self.load_status()

    def load_status(self):
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        return {"invested": False}

    def save_status(self):
        with open(STATUS_FILE, "w") as f:
            json.dump(self.status, f)

    def has_invested(self):
        return self.status.get("invested", False)

    def mark_invested(self):
        self.status["invested"] = True
        self.save_status()


# Beispiel-Nutzung:
if __name__ == "__main__":
    tracker = LongtermTracker()
    if not tracker.has_invested():
        print("Noch nicht investiert – führe Invest aus...")
        tracker.mark_invested()
    else:
        print("✅ Bereits investiert.")
