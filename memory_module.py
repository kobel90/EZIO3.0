from typing import Dict, Any, List
import os
import json
from datetime import datetime
from typing import Optional

class MemoryModule:
    def __init__(self, speicherpfad: str = "memory/"):
        self.speicherpfad = speicherpfad
        os.makedirs(self.speicherpfad, exist_ok=True)
        self.aktueller_tag = datetime.now().strftime("%Y-%m-%d")
        self.gespeicherte_daten: Dict[str, List[Dict[str, Any]]] = {}

    def speichere_signal(self, epic: str, signal: Dict[str, Any]):
        """Speichert ein neues Signal für ein Epic."""
        if epic not in self.gespeicherte_daten:
            self.gespeicherte_daten[epic] = []

        self.gespeicherte_daten[epic].append(signal)
        self._persistiere(epic)

    def lade_signale(self, epic: str) -> List[Dict[str, Any]]:
        """Lädt gespeicherte Signale aus Datei."""
        dateiname = f"{epic}_{self.aktueller_tag}.json"
        pfad = os.path.join(self.speicherpfad, dateiname)

        if not os.path.exists(pfad):
            return []

        try:
            with open(pfad, "r") as f:
                daten = json.load(f)
                self.gespeicherte_daten[epic] = daten
                return daten
        except Exception as e:
            print(f"❌ Fehler beim Laden von {pfad}: {e}")
            return []

    def gib_letztes_signal(self, epic: str) -> Dict[str, Any]:
        """Gibt das letzte gespeicherte Signal eines Epics zurück (wenn vorhanden)."""
        daten = self.gespeicherte_daten.get(epic) or self.lade_signale(epic)
        if not daten:
            return {}

        return daten[-1] if daten else {}

    def loesche_signale(self, epic: Optional[str] = None):
        """Löscht gespeicherte Signale im Speicher (optional nur für ein Epic)."""
        if epic:
            if epic in self.gespeicherte_daten:
                del self.gespeicherte_daten[epic]
                print(f"🧹 Speicher für {epic} geleert.")
        else:
            self.gespeicherte_daten.clear()
            print("🧹 Gesamter Memory-Speicher geleert.")

    def _persistiere(self, epic: str):
        """Speichert aktuelle Daten persistent in eine JSON-Datei."""
        dateiname = f"{epic}_{self.aktueller_tag}.json"
        pfad = os.path.join(self.speicherpfad, dateiname)

        try:
            with open(pfad, "w") as f:
                json.dump(self.gespeicherte_daten.get(epic, []), f, indent=2)
            print(f"💾 Daten für {epic} gespeichert in {pfad}")
        except Exception as e:
            print(f"❌ Fehler beim Speichern der Daten für {epic}: {e}")

    def lade_alle_epics(self):
        """
        Lädt alle gespeicherten Epic-Daten aus dem Speicherpfad in den Arbeitsspeicher.
        """
        dateien = [f for f in os.listdir(self.speicherpfad) if f.endswith(".json")]
        geladen = 0

        for datei in dateien:
            pfad = os.path.join(self.speicherpfad, datei)
            try:
                with open(pfad, "r") as f:
                    daten = json.load(f)
                    if isinstance(daten, list) and daten:
                        epic = datei.split("_")[0]
                        self.gespeicherte_daten[epic] = daten
                        geladen += 1
            except Exception as e:
                print(f"⚠️ Fehler beim Laden von {datei}: {e}")

        print(f"📂 {geladen} gespeicherte Epics aus Speicher geladen.")

    def speichere_alle_epics(self):
        """
        Speichert alle geladenen Epic-Daten aus dem Speicher in separate JSON-Dateien.
        """
        gespeichert = 0
        for epic, daten in self.gespeicherte_daten.items():
            if not daten:
                continue
            try:
                dateiname = f"{epic}_history.json"
                pfad = os.path.join(self.speicherpfad, dateiname)
                with open(pfad, "w") as f:
                    json.dump(daten, f, indent=2)
                gespeichert += 1
            except Exception as e:
                print(f"❌ Fehler beim Speichern von {epic}: {e}")

        print(f"💾 {gespeichert} Epics erfolgreich gespeichert.")

    def speichere_als_dict(self) -> Dict[str, List[str]]:
        return self.memory

    def lade_aus_dict(self, daten: Dict[str, List[str]]):
        self.memory = daten

    def speichere_ereignis(self, epic: str, text: str):
        """Speichert ein Ereignis (z. B. Analyse oder Info) im Verlauf"""
        eintrag = {
            "zeit": datetime.now().isoformat(),
            "text": text
        }

        if epic not in self.gespeicherte_daten:
            self.gespeicherte_daten[epic] = []

        self.gespeicherte_daten[epic].append(eintrag)
        self._persistiere(epic)

    def zeige_verlauf(self, epic: str) -> List[str]:
        """Gibt die gespeicherten Text-Ereignisse für ein EPIC zurück"""
        daten = self.gespeicherte_daten.get(epic) or self.lade_signale(epic)
        return [eintrag["text"] for eintrag in daten if "text" in eintrag]

    def speichere(self, epic: str, info: Dict[str, Any]):
        """Speichert generische Info-Objekte in den Verlauf"""
        eintrag = {"zeit": datetime.now().isoformat()}
        eintrag.update(info)

        if epic not in self.gespeicherte_daten:
            self.gespeicherte_daten[epic] = []

        self.gespeicherte_daten[epic].append(eintrag)
        self._persistiere(epic)

    def lade_verlauf(self, epic: str) -> List[Dict[str, Any]]:
        """Lädt alle gespeicherten Einträge für ein Epic."""
        return self.gespeicherte_daten.get(epic) or self.lade_signale(epic)

    def log_preisquelle(self, epic: str, quelle: str):
        eintrag = {
            "typ": "preisquelle",
            "quelle": quelle,
            "zeit": datetime.now().isoformat()
        }
        self.speichere(epic, eintrag)