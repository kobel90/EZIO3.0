import csv
import os
import datetime
from zielkontrolle import ZielKontrolle
from plyer import notification
from datetime import datetime

class GUVChecker:
    def __init__(self, logdatei="guv_log.csv", ziel_csv="zielplan.csv"):
        self.logdatei = logdatei
        self.kontrolle = ZielKontrolle(ziel_csv)

    def lade_letzten_stand(self):
        if not os.path.exists(self.logdatei):
            return None

        with open(self.logdatei, mode='r') as file:
            reader = csv.DictReader(file)
            zeilen = list(reader)
            if zeilen:
                return float(zeilen[-1]["Balance"])
        return None

    def logge_balance(self, heutiges_datum, balance):
        existiert = os.path.exists(self.logdatei)
        with open(self.logdatei, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not existiert:
                writer.writerow(["Datum", "Balance"])
            writer.writerow([heutiges_datum, balance])

    def berechne_guv(self, aktuelle_balance):
        gestrige_balance = self.lade_letzten_stand()
        heutiges_datum = datetime.today().strftime("%Y-%m-%d")
        self.logge_balance(heutiges_datum, aktuelle_balance)

        if gestrige_balance is None:
            print("🔄 Kein Vergleichswert gefunden. GUV-Berechnung übersprungen.")
            return 0.0

        guv = aktuelle_balance - gestrige_balance
        print(f"📊 Tages-GUV: {guv:.2f}")

        # Zielvergleich
        status = self.kontrolle.bewertung(guv)
        print(f"📌 Zielstatus: {status}")

        if "Verlustgrenze erreicht" in status:
            print("🛑 Bot sollte gestoppt werden!")
            # Hier könnte z. B. ein Notstopp-Flag gesetzt oder Trade-Logik deaktiviert werden

        return guv

# Beispiel-Test (nur zur Demonstration):
if __name__ == "__main__":
    checker = GUVChecker()
    test_balance = 115.50
    checker.berechne_guv(test_balance)
