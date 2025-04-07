
import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# === KONFIGURATION ===
WATCH_PATH = "."  # Projektverzeichnis beobachten
GIT_COMMIT_MESSAGE = "Automatischer Commit von EZIO Gitwatch"
SLEEP_INTERVAL = 5  # Sekunden zwischen Scans

class GitAutoHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        if ".git" in event.src_path:
            return
        print(f"📝 Änderung erkannt: {event.src_path}")
        os.system("git add .")
        os.system(f'git commit -m "{GIT_COMMIT_MESSAGE}"')
        os.system("git push origin main")
        print("✅ Änderungen gepusht.")

if __name__ == "__main__":
    path = WATCH_PATH
    print(f"🔍 Beobachte Änderungen in: {os.path.abspath(path)}")
    event_handler = GitAutoHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(SLEEP_INTERVAL)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
