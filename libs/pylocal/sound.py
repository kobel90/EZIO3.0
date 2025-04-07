import os
import platform
import subprocess

def play_sound(file_path):
    if not os.path.exists(file_path):
        print("❌ Sounddatei nicht gefunden:", file_path)
        return

    system = platform.system()

    try:
        if system == "Darwin":
            subprocess.run(["afplay", file_path])
        elif system == "Linux":
            subprocess.run(["aplay", file_path])
        elif system == "Windows":
            import winsound
            winsound.PlaySound(file_path, winsound.SND_FILENAME)
        else:
            print("❌ Kein unterstützter Soundplayer gefunden.")
    except Exception as e:
        print("❌ Fehler beim Abspielen des Sounds:", e)