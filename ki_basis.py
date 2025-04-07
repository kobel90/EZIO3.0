# ki_basis.py

import os
import json
import random
import datetime
from typing import Dict, List, Optional

class ki_basis:
    def __init__(self, name: str, memory_path: str = "ki_memory.json"):
        self.name = name
        self.memory_path = memory_path
        self.memory: Dict = self._load_memory()
        self.log_file = f"log_{self.name.lower()}.txt"

    def _load_memory(self) -> Dict:
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Fehler beim Laden des Speichers: {e}")
        return {}

    def _save_memory(self) -> None:
        try:
            with open(self.memory_path, "w") as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            print(f"❌ Fehler beim Speichern des Speichers: {e}")

    def log(self, message: str) -> None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
        print(f"🧠 {self.name}: {message}")

    def remember(self, key: str, value: str) -> None:
        self.memory[key] = value
        self._save_memory()
        self.log(f"Erinnert sich an {key} = {value}")

    def recall(self, key: str) -> Optional[str]:
        value = self.memory.get(key)
        self.log(f"Ruft Erinnerung {key} ab: {value}")
        return value

    def react_to_input(self, input_text: str) -> str:
        # Dummy-Intelligenz: erkennt Fragen und Begriffe
        if "wie" in input_text.lower():
            response = "Ich denke nach... vielleicht können News dabei helfen."
        elif "bitcoin" in input_text.lower():
            response = "BTC ist spannend. Ich beobachte den Markt."
        else:
            response = random.choice([
                "Verstanden. Ich beobachte weiter.",
                "Interessant... ich speichere das.",
                "Das könnte wichtig sein.",
                "Ich werde das bei der nächsten Entscheidung berücksichtigen."
            ])
        self.log(f"Input verarbeitet: {input_text} → Antwort: {response}")
        return response

    def update_knowledge(self, new_data: Dict) -> None:
        self.memory.update(new_data)
        self._save_memory()
        self.log(f"Lerninhalt aktualisiert: {list(new_data.keys())}")

    def clear_memory(self) -> None:
        self.memory = {}
        self._save_memory()
        self.log("🧽 Speicher gelöscht.")

if __name__ == "__main__":
    ki = ki_basis("EzioKI")
    ki.react_to_input("Wie steht es um Bitcoin heute?")
    ki.remember("letzter_Trade_BTC", "2025-04-03")
    ki.recall("letzter_Trade_BTC")
