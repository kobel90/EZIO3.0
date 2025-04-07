
from trading_ki import TradingKI
from capital_api import CapitalComAPI
import pandas as pd
import json

with open("config.json") as f:
    config = json.load(f)

api = CapitalComAPI(
    api_key=config["api_key"],
    account_id=config["account_id"],
    password=config["password"]
)

def simuliere_backtest(epic: str):
    preise = api.get_price_history(epic=epic, limit=100)
    print("🔍 Preisantwort:", preise)
    if "prices" not in preise:
        print(f"⚠️ Kein 'prices' in API-Antwort für {epic}: {preise}")
        return
    df = pd.DataFrame(preise["prices"])  # je nach Aufbau evtl. ["prices"]

    # 🧠 KI starten
    ki = TradingKI()
    gewinne = []
    verluste = []

    for index, row in df.iterrows():
        preis = row["close"]
        volumen = row["volume"]

        eingabe = {
            "price": preis,
            "volumen": volumen,
            "volumen_schnitt": 950000,
            "rsi": 52,
            "macd": 0.7,
            "volatilitaet": 1.8,
            "fibonacci": 178,
            "support": 175,
            "resistance": 180
        }

        entscheidung = ki.analysiere_signal(eingabe)

        if entscheidung == "KAUFEN":
            gewinne.append(1)
        elif entscheidung == "VERKAUFEN":
            verluste.append(1)

    print(f"✅ {epic}-Backtest abgeschlossen.")
    print(f"📊 Trades: {len(gewinne)+len(verluste)}, Käufe: {len(gewinne)}, Verluste: {len(verluste)}")

def teste_epics():
    epic_liste = [
        "XRPUSD", "BTCUSD", "ETHUSD", "US500", "EURUSD", "USDJPY", "TSLA",
        "AAPL", "MSFT", "AMZN", "META", "NVDA", "GBPUSD", "AUDUSD", "USDCHF"
    ]

    gueltige_epics = []

    for epic in epic_liste:
        print(f"🔍 Teste Epic: {epic}")
        preise = api.get_price_history(epic=epic, limit=5)
        print(f"➡️ Antwort: {preise}")
        if "prices" in preise:
            print(f"✅ Erfolgreich: {epic} liefert {len(preise['prices'])} Preiseinträge\n")
            gueltige_epics.append(epic)
        else:
            print(f"❌ Kein 'prices' gefunden für {epic}. Antwort: {preise}\n")

    # Optional direkt Backtests anschließen:
    for epic in gueltige_epics:
        simuliere_backtest(epic)

if __name__ == "__main__":
    api = CapitalComAPI(
        api_key=config["api_key"],
        account_id=config["account_id"],
        password=config["password"]
    )
    print("📊 Verfügbare EPICs:")
    print(api.get_all_markets())
    preise = api.get_price_history(epic="XRPUSD", limit=5)
