# generate_overview.py
import os
from datetime import datetime

# Beschreibungen für bekannte Dateien
beschreibungen = {
    "trading_bot.py": "Hauptlogik des Tradingbots, führt Orders aus",
    "trading_bot_v2.py": "Alternative/erweiterte Version des Tradingbots",
    "zielplan_generator.py": "Erstellt CSV-Zielplan basierend auf Startkapital",
    "zielkontrolle.py": "Lädt und prüft Tagesziel aus Zielplan",
    "guv_log.csv": "Protokollierter Gewinn/Verlust pro Trade",
    "guv_logger.py": "Schreibt Einträge in guv_log.csv nach jedem Trade",
    "guv_plotter.py": "Visualisiert GuV-Daten aus CSV-Dateien",
    "guv_checker.py": "Überprüft aktuelle GuV-Werte während des Tages",
    "status_panel.py": "GUI-Panel für Echtzeitstatus & Bot-Kontrolle",
    "ezio_startmenu.py": "Startmenü im Pixelstil für die App",
    "capital_api.py": "Verwaltet Kapitalverteilung und Rückmeldung",
    "longterm_tracker.py": "Noch in Entwicklung – Langzeitüberwachung",
    "longterm_status.json": "Statusdaten für langfristige Strategie",
    "starte_bot.command": "Shell-Script zum Starten des Bots auf macOS",
    "zielplan.csv": "CSV-Zielplan mit täglichem Zielwert",
}

# Zielpfad für Übersicht
output_file = "tools_overview.md"

# Alle relevanten Dateien auflisten
projektdateien = sorted([
    f for f in os.listdir()
    if f.endswith((".py", ".csv", ".json", ".command", ".txt"))
])

# Übersicht schreiben
with open(output_file, "w") as f:
    f.write("# EZIO - Tools Übersicht\n\n")
    f.write(f"> Automatisch generiert am {datetime.now().strftime('%Y-%m-%d')}\n\n")
    f.write("| Datei | Beschreibung |\n")
    f.write("|-------|--------------|\n")
    for datei in projektdateien:
        beschreibung = beschreibungen.get(datei, "–")
        f.write(f"| `{datei}` | {beschreibung} |\n")

print(f"✅ tools_overview.md erfolgreich generiert ({len(projektdateien)} Dateien)")