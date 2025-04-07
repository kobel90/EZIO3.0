import itertools
import sys
import time
import threading

class Spinner:
    def __init__(self, text="Wird geladen...", delay=0.1):
        self.spinner = itertools.cycle(["|", "/", "-", "\\"])
        self.delay = delay
        self.text = text
        self.running = False
        self.thread = None

    def spin(self):
        while self.running:
            sys.stdout.write(f"\r{next(self.spinner)} {self.text}")
            sys.stdout.flush()
            time.sleep(self.delay)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.spin)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write("\r✔️ Fertig!\n")
        sys.stdout.flush()