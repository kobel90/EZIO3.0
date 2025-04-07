import os
import platform
import subprocess
import pygame

class SoundPlayer:

    @staticmethod
    def play(file_path):
        if platform.system() == "Darwin":
            subprocess.run(["afplay", file_path])
        elif platform.system() == "Linux":
            subprocess.run(["aplay", file_path])
        elif platform.system() == "Windows":
            import winsound
            winsound.PlaySound(file_path, winsound.SND_FILENAME)
        else:
            print("❌ Kein kompatibler Soundplayer gefunden.")

    class SoundPlayer:
        @staticmethod
        def spiele_startsound(pfad="libs/richlocal/sounds/startsound.wav"):
            if not os.path.exists(pfad):
                print("❌ Startsound nicht gefunden:", pfad)
                return

            pygame.mixer.init()
            pygame.mixer.music.load(pfad)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)