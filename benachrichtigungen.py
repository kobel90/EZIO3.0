# benachrichtigungen.py
import os
import platform

try:
    from playsound import playsound
except ImportError:
    playsound = None

def popup_nachricht(titel: str, text: str):
    if platform.system() == "Darwin":  # macOS
        os.system(f"""osascript -e 'display notification "{text}" with title "{titel}"'""")
    elif platform.system() == "Windows":
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(titel, text, duration=5)

def spiele_ton(dateipfad: str = "alarm.mp3"):
    if callable(playsound):
        playsound(dateipfad)
    else:
        print("🔕 Kein Soundmodul installiert. (playsound fehlt)")
