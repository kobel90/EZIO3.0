# libs/richlocal/progressbar.py

# libs/richlocal/progressbar.py

import time
import sys

class GlitchProgressBar:
    def start(self):
        for i in range(21):
            bar = "▓" * i + "░" * (20 - i)
            sys.stdout.write(f"\r[Glitch] [{bar}] {i*5}%")
            sys.stdout.flush()
            time.sleep(0.1)
        print("\n")

class LaserProgressBar:
    def start(self):
        for i in range(21):
            bar = "🟥" * i + "⬛" * (20 - i)
            sys.stdout.write(f"\r[Laser]  [{bar}] {i*5}%")
            sys.stdout.flush()
            time.sleep(0.08)
        print("\n")

class DNAProgressBar:
    def start(self):
        for i in range(21):
            pattern = "🧬" * i + "·" * (20 - i)
            sys.stdout.write(f"\r[DNA]    [{pattern}] {i*5}%")
            sys.stdout.flush()
            time.sleep(0.12)
        print("\n")