import schedule
import time
from zielplan_generator import generiere_zielplan

def update_zielplan():
    print("🔄 Automatisches Zielplan-Update gestartet...")
    generiere_zielplan(start_betrag=30.0, tage=30, wachstum_min=0.05, wachstum_max=0.07)

# Jeden Montag um 06:00 Uhr
schedule.every().monday.at("06:00").do(update_zielplan)

print("🕓 Warte auf nächsten Montag 06:00 ... (zum Testen einfach Zeit ändern)")

# Endlos-Loop
while True:
    schedule.run_pending()
    time.sleep(30)