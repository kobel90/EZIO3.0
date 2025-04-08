# ezio_startmenü.py
import sys
import os
os.environ["TERM"] = "xterm-color"
import time
import subprocess
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if base_path not in sys.path:
    sys.path.insert(0, base_path)
from richlocal.console import Console
from richlocal.panel import Panel
from richlocal.text import Text
from richlocal.prompt import Prompt
from richlocal import spinner
from richlocal.console import Console
from richlocal.soundplayer import SoundPlayer
SoundPlayer.spiele_startsound()
from pylocal import sound

sound.play_sound("libs/richlocal/sounds/startsound.wav")
import threading

import richlocal.console
print("[DEBUG] Lokalmodul geladen:", richlocal.console.__file__)

import random
from richlocal.progressbar import GlitchProgressBar, LaserProgressBar, DNAProgressBar

bar = random.choice([GlitchProgressBar(), LaserProgressBar(), DNAProgressBar()])
bar.start()


spinner_instance = spinner.Spinner("EZIO wird vorbereitet...")
spinner_instance.start()
time.sleep(2)
spinner_instance.stop()

SoundPlayer.spiele_startsound()
print("✅ Sound gestartet.")

console = Console()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    ascii_text = """
███████╗███████╗██╗███████╗ ██████╗     
██╔════╝██╔════╝██║██╔════╝██╔════╝     
███████╗█████╗  ██║█████╗  ██║  ███╗    
╚════██║██╔══╝  ██║██╔══╝  ██║   ██║    
███████║███████╗██║███████╗╚██████╔╝    
╚══════╝╚══════╝╚═╝╚══════╝ ╚═════╝ 
"""
    panel = Panel(Text(ascii_text, style="bold magenta"), title="[yellow]EZIO 4.0 – KI-Trading Engine", expand=False)
    console.print(panel)

def main_menu():
    while True:
        clear_screen()
        print_banner()

        console.print("\n[cyan]1.[/] START EZIO TRADINGBOT")
        console.print("[cyan]2.[/] AVELINE (Manueller Lernmodus)")
        console.print("[cyan]3.[/] ALOY (Automatischer Lernmodus)")
        console.print("[cyan]4.[/] SL/TP EDITOR")
        console.print("[cyan]5.[/] STATUS & ZIEL EINSTELLUNGEN")
        console.print("[red]6.[/] EXIT")

        auswahl = Prompt.ask(
            "\n[bold]Auswahl[/bold]",
            choices=["1", "2", "3", "4", "5", "6"],
            default="1"
        )

        if auswahl == "1":
            os.system("python3 trading_bot_V4.py")
        elif auswahl == "2":
            os.system("python3 trading_bot_V4.py")
        elif auswahl == "3":
            os.system("python3 trading_bot_V4.py auto")
        elif auswahl == "4":
            try:
                from sl_tp_editor import SLTPEditor
                import tkinter as tk
                fenster = tk.Tk()
                fenster.title("SL/TP Editor")
                app = SLTPEditor(fenster)
                fenster.mainloop()
            except Exception as e:
                console.print(f"[red]Fehler beim Starten des SL/TP Editors:[/red] {e}")
                input("\nDrücke Enter zum Zurückkehren...")
        elif auswahl == "5":
            try:
                import tkinter as tk
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
                from status_settings_gui import starte_gui
                starte_gui()
            except Exception as e:
                console.print(f"[red]Fehler beim Starten der Status-GUI:[/red] {e}")
                input("\nDrücke Enter zum Zurückkehren...")
        elif auswahl == "6":
            console.print("\n👋 [bold red]Bis bald, Commander![/bold red]")
            sys.exit(0)

def play_startsound():
    pygame.mixer.init()
    pygame.mixer.music.load("libs/richlocal/sounds/startsound.wav")
    pygame.mixer.music.play()

    # Startsound im Hintergrund abspielen
    threading.Thread(target=play_startsound).start()

def zurueck_zum_menue(self):
    self.master.destroy()
    try:
        # Passe den Pfad zum Startmenü an (hier: start/ezio_startmenü.py)
        startmenue_pfad = os.path.join(os.path.dirname(__file__), "start", "ezio_startmenü.py")
        subprocess.Popen(["python3", startmenue_pfad])
    except Exception as e:
        print(f"⚠️ Fehler beim Zurückkehren zum Menü: {e}")

if __name__ == "__main__":
    main_menu()
    input("\n[bold]Drücke Enter zum Beenden...[/bold]")