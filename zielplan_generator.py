import pandas as pd
from datetime import datetime, timedelta
import random

def generiere_zielplan(start_betrag: float = 30.0,
                       tage: int = 30,
                       wachstum_min: float = 0.05,
                       wachstum_max: float = 0.07,
                       pfad: str = "zielplan.csv") -> None:
    """Erzeugt automatisch einen Zielplan mit täglich steigendem Zielbetrag."""
    heute = datetime.today().date()
    zielplan = []

    betrag = start_betrag

    for tag in range(tage):
        datum = heute + timedelta(days=tag)
        zielplan.append({
            "Tag": tag + 1,
            "Datum": datum,
            "Zielbetrag": round(betrag, 2)
        })

        wachstum = random.uniform(wachstum_min, wachstum_max)
        betrag *= (1 + wachstum)

    df = pd.DataFrame(zielplan)
    df.to_csv(pfad, index=False)
    print(f"✅ Zielplan für {tage} Tage erstellt: {pfad}")

# Direkt-Test
if __name__ == "__main__":
    generiere_zielplan(start_betrag=30.0, tage=30, wachstum_min=0.05, wachstum_max=0.07)