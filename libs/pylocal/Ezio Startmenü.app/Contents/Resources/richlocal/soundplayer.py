# libs/richlocal/soundplayer.py
import os
import platform
import subprocess

class SoundPlayer:
    @staticmethod
    def spiele_startsound(pfad="libs/richlocal/sounds/startsound.wav"):
        if not os.path.exists(pfad):
            print("❌ Startsound nicht gefunden:", pfad)
            return

        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                subprocess.run(["afplay", pfad])
            elif system == "Linux":
                subprocess.run(["aplay", pfad])
            elif system == "Windows":
                import winsound
                winsound.PlaySound(pfad, winsound.SND_FILENAME)
            else:
                print("❌ Kein kompatibler Soundplayer gefunden.")
        except Exception as e:
            print("❌ Sound konnte nicht abgespielt werden:", e)