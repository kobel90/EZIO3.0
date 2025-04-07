
import time
import requests
import json
from datetime import datetime

API_URL = "http://localhost:5000/status"  # oder dein API-Endpunkt
EXPORT_PATH = "ezio_auto_status.json"
INTERVAL = 300  # alle 5 Minuten

def exportiere_status():
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            daten = response.json()
            with open(EXPORT_PATH, "w") as f:
                json.dump(daten, f, indent=4)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Daten erfolgreich gespeichert.")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Fehlercode: {response.status_code}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Fehler beim Abruf: {e}")

if __name__ == "__main__":
    print("🔄 EZIO Auto-Exporter gestartet...")
    while True:
        exportiere_status()
        time.sleep(INTERVAL)
