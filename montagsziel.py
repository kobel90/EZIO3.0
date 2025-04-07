from datetime import datetime, timedelta
import csv
import os

def generiere_zielplan(eigenkapital: float, ziel_prozent: float = 0.10, pfad="zielplan.csv"):
    verwendbar = eigenkapital * (2 / 3)
    tagesziel = verwendbar * ziel_prozent

    heute = datetime.now()
    montag = heute - timedelta(days=heute.weekday())

    zielplan = []
    for i in range(7):
        tag = montag + timedelta(days=i)
        zielplan.append({
            "Datum": tag.strftime("%Y-%m-%d"),
            "Ziel": f"{tagesziel:.2f}"
        })

    with open(pfad, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["Datum", "Ziel"])
        writer.writeheader()
        writer.writerows(zielplan)

def pruefe_und_generiere(eigenkapital: float, ziel_prozent: float = 0.10, pfad="zielplan.csv"):
    heute = datetime.now()
    if heute.weekday() == 0 and heute.hour >= 6:  # Montag ab 06:00 Uhr
        if not os.path.exists(pfad) or not ist_heutiger_plan_aktuell(pfad, heute):
            generiere_zielplan(eigenkapital, ziel_prozent, pfad)
            print("✅ Neuer Zielplan erstellt.")
        else:
            print("ℹ️ Zielplan bereits aktuell.")
    else:
        print("⏳ Noch nicht Montag 06:00 Uhr – keine Aktualisierung.")

def ist_heutiger_plan_aktuell(pfad, heute):
    try:
        with open(pfad, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["Datum"] == heute.strftime("%Y-%m-%d"):
                    return True
    except:
        return False
    return False