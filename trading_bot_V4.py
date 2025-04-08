# trading_bot_v4.py

import pandas as pd
import time
import json
import os
import traceback
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from colorama import init, Fore, Style
from utils.whitelist_loader import load_whitelist, update_whitelist
from zielkontrolle import ZielKontrolle
from trading_ki import TradingKI
from sltp_manager import SLTPManager
from utils.price_source_manager import PriceSourceManager
from utils.config_loader import load_config
from benachrichtigungen import popup_nachricht, spiele_ton
from strategie_engineV2 import berechne_zielbereiche
from utils.epic_mapper import update_epic_mapping
from utils.whitelist_loader import load_whitelist
from chart_analyzer import ChartAnalyzer
from utils.config_loader import load_config
config = load_config()
import pprint
from strategie_engineV2 import (
    calculate_sma,
    berechne_volatilitaet_preise,
    schaetze_trade_dauer,
    ist_einstieg_geeignet,
    ermittle_richtung,
)

from capital_api import CapitalComAPI
from longterm_tracker import LongtermTracker
from gui.aggression_control import AggressionControlGUI

init()  # Colorama aktivieren


class TradingBotV4:
    def __init__(self, api: CapitalComAPI, capital: float, position_size: float = 1.0, aggressive_mode: bool = False):
        import json

        # === System-Setup ===
        self.api = api
        self.capital = capital
        self.position_size = position_size
        self.aggressive_mode = aggressive_mode
        self.running = True
        self.live_mode = False  # 🔒 Nur auf True setzen, wenn bewusst live traden!
        self.chart_analyzer = ChartAnalyzer()

        # === Config laden ===
        with open("config.json") as f:
            config = json.load(f)
        trading_config = config.get("trading_params", {})

        self.load_sl_tp_config()

        # === Module ===
        self.longterm_tracker = LongtermTracker()
        self.trading_ki = TradingKI()
        self.price_manager = PriceSourceManager()
        self.strategy_mode = load_config().get("strategie_modus", "classic")
        self.whitelist = load_whitelist()
        epic_list = list(self.whitelist.keys())
        update_epic_mapping(epic_list)
        self.sltp_manager = SLTPManager(config_path="sl_tp_config.json", history_path="sl_tp_history.json")

        # === Dashboard / Signale ===
        self.signals = []
        self.last_status_update = datetime.now()
        self.status_update_interval = 5
        self.analysis_interval = 15

        # === Kapital & Margin ===
        self.available_margin = 0.0
        self.total_equity = 0.0
        self.used_margin = 0.0
        self.pnl_ratio = 0.0

        # 💡 Aus config.json dynamisch laden (inkl. Fallback)
        self.asset_params = trading_config
        self.stop_loss_pct = trading_config.get("default", {}).get("stop_loss_percent", 0.03)
        self.take_profit_pct = trading_config.get("default", {}).get("take_profit_percent", 0.05)

        # === Performance-Tracking ===
        self.total_profit = 0.0
        self.hourly_profit = 0.0
        self.positions_opened = 0
        self.positions_closed = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.trade_history = []
        self.max_trade_history = 50
        self.last_hour_check = datetime.now()

        # === RSI / MACD Settings ===
        self.rsi_period = 14
        self.rsi_oversold = 20
        self.rsi_overbought = 80
        self.macd_fast = 8
        self.macd_slow = 21
        self.macd_signal = 5

        # === Spezialparameter für XRP (nur falls gebraucht) ===
        self.xrp_params = {
            "position_size": 8.0,
            "rsi_oversold": 25,
            "rsi_overbought": 75,
            "stop_loss_percent": 5.0,
            "take_profit_percent": 12.0
        }

        # === Märkte ===
        self.markets = [
            {"epic": "XRPUSD", "instrumentName": "Ripple/USD", "leverage": 20},
            {"epic": "BTCUSD", "instrumentName": "Bitcoin/USD", "leverage": 20},
            {"epic": "ETHUSD", "instrumentName": "Ethereum/USD", "leverage": 20},
            {"epic": "US500", "instrumentName": "S&P 500", "leverage": 20},
            {"epic": "EURUSD", "instrumentName": "EUR/USD", "leverage": 20},
            {"epic": "USDJPY", "instrumentName": "USD/JPY", "leverage": 20},
            {"epic": "TSLA", "instrumentName": "Tesla Inc", "leverage": 20},
            {"epic": "AAPL", "instrumentName": "Apple Inc", "leverage": 20},
            {"epic": "MSFT", "instrumentName": "Microsoft", "leverage": 20},
            {"epic": "AMZN", "instrumentName": "Amazon", "leverage": 20},
            {"epic": "META", "instrumentName": "Meta Platforms", "leverage": 20},
            {"epic": "NVDA", "instrumentName": "NVIDIA", "leverage": 20},
            {"epic": "GBPUSD", "instrumentName": "GBP/USD", "leverage": 20},
            {"epic": "AUDUSD", "instrumentName": "AUD/USD", "leverage": 20},
            {"epic": "USDCHF", "instrumentName": "USD/CHF", "leverage": 20},
        ]

        # === Offene Trades ===
        self.active_trades = {}

        # ✅ Dashboard-Export erst am Ende aufrufen
        self.exportiere_dashboard_status()

    @staticmethod
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')

    def stop(self):
        self.running = False
        print(f"{Fore.YELLOW}🛑 Trading Bot wird gestoppt...{Style.RESET_ALL}")

    def check_margin(self):
        try:
            account_info = self.api.get_account_info()
            for account in account_info.get("accounts", []):
                if account["currency"] == "CHF":
                    self.available_margin = float(account["balance"]["available"])
                    self.total_equity = float(account["balance"]["balance"])
                    self.used_margin = self.total_equity - self.available_margin
                    if self.losing_trades > 0:
                        self.pnl_ratio = self.winning_trades / self.losing_trades
                    else:
                        self.pnl_ratio = float('inf') if self.winning_trades > 0 else 0
                    break
        except Exception as e:
            print(f"{Fore.RED}Fehler bei der Margin-Abfrage: {e}{Style.RESET_ALL}")

    def print_status(self):
        self.clear_screen()
        print(f"{Fore.CYAN}=== EZIO TRADING BOT V4 ==={Style.RESET_ALL}")
        print(f"Zeit: {datetime.now().strftime('%H:%M:%S')}")
        print(f"Status: {Fore.GREEN}AKTIV{Style.RESET_ALL}\n")

        modus = '🟥 AGGRESSIV' if self.aggressive_mode else '🟩 DEFENSIV'
        print(f"{Fore.MAGENTA}Modus: {modus}{Style.RESET_ALL}")

        print(f"{Fore.YELLOW}=== KAPITAL ==={Style.RESET_ALL}")
        print(f"Verfügbare Margin: {Fore.GREEN}{self.available_margin:.2f} CHF{Style.RESET_ALL}")
        print(f"Eigenkapital: {Fore.GREEN}{self.total_equity:.2f} CHF{Style.RESET_ALL}")
        print(f"Genutzte Margin: {Fore.RED}{self.used_margin:.2f} CHF{Style.RESET_ALL}")
        print(f"G/V Verhältnis: {Fore.GREEN if self.pnl_ratio >= 1 else Fore.RED}{self.pnl_ratio:.2f}{Style.RESET_ALL}\n")

        print(f"{Fore.YELLOW}=== PERFORMANCE ==={Style.RESET_ALL}")
        win_rate = (self.winning_trades / self.positions_closed * 100) if self.positions_closed > 0 else 0
        print(f"Gesamtprofit: {Fore.GREEN if self.total_profit >= 0 else Fore.RED}{self.total_profit:.2f} CHF{Style.RESET_ALL}")
        print(f"Stündlicher Profit: {Fore.GREEN if self.hourly_profit >= 0 else Fore.RED}{self.hourly_profit:.2f} CHF{Style.RESET_ALL}")
        print(f"Gewinnrate: {Fore.GREEN if win_rate >= 50 else Fore.RED}{win_rate:.2f}%{Style.RESET_ALL}")
        print(f"Gewinn-Trades: {Fore.GREEN}{self.winning_trades}{Style.RESET_ALL} | Verlust-Trades: {Fore.RED}{self.losing_trades}{Style.RESET_ALL}\n")

        print(f"{Fore.YELLOW}=== LETZTE TRADES ==={Style.RESET_ALL}")
        for trade in self.trade_history[-5:]:
            color = Fore.GREEN if trade['profit'] >= 0 else Fore.RED
            profit = trade.get("profit")
            print(
                f"{trade['time']} | {trade['epic']} | {trade['direction']} | "
                f"Profit: {color}{profit:.2f} USD{Style.RESET_ALL}" if profit is not None
                else f"{trade['time']} | {trade['epic']} | {trade['direction']} | Profit: {Fore.YELLOW}n/a{Style.RESET_ALL}"
            )
            if self.trading_ki.signals:
                letztes_signal = self.trading_ki.signals[-1]
                print(
                    f"{Fore.BLUE}Letztes Signal → {letztes_signal['epic']} | {letztes_signal['direction']} | Conf: {letztes_signal['confidence']} | Size: {letztes_signal['size']}{Style.RESET_ALL}")
                verlauf = self.trading_ki.memory.lade_verlauf("lerntext")
                if verlauf:
                    letzter = verlauf[-1]
                    quelle = letzter.get("quelle", "unbekannt")
                    analyse = letzter.get("analyse", {})
                    print(f"{Fore.MAGENTA}Letzter Lerntext → Quelle: {quelle} | Analyse: {analyse}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.MAGENTA}Kein Lerntext im Verlauf.{Style.RESET_ALL}")
                    if os.path.exists("guv_log.csv"):
                        try:
                            with open("guv_log.csv", "r") as f:
                                lines = f.readlines()
                                if len(lines) > 1:
                                    letzte_zeile = lines[-1].strip().split(";")
                                    if len(letzte_zeile) >= 3:
                                        datum, epic, gewinn = letzte_zeile
                                        print(
                                            f"{Fore.YELLOW}Letzter G/V → {gewinn} CHF ({epic} am {datum}){Style.RESET_ALL}")
                        except:
                            print("⚠️ GUV-Datei konnte nicht gelesen werden.")

            else:
                print(f"{Fore.BLUE}Noch kein Signal vorhanden.{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Nächstes Status-Update in {self.status_update_interval} Sekunden...{Style.RESET_ALL}")

    def add_trade_to_history(self, epic: str, direction: str, profit: float):
        self.trade_history.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "epic": epic,
            "direction": direction,
            "profit": profit
        })
        if len(self.trade_history) > self.max_trade_history:
            self.trade_history.pop(0)

    def calculate_indicators(self, prices: pd.Series) -> Tuple[float, float, float]:
        try:
            if prices is None or prices.empty:
                print("⚠️ Leere Preisreihe übergeben.")
                return 50.0, 0.0, 0.0  # Fallback

            # RSI-Berechnung
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            rsi_series = 100 - (100 / (1 + rs))

            # MACD-Berechnung
            exp1 = prices.ewm(span=self.macd_fast, adjust=False).mean()
            exp2 = prices.ewm(span=self.macd_slow, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=self.macd_signal, adjust=False).mean()

            # Letzte Werte robust extrahieren
            rsi_val = rsi_series.dropna().iloc[-1] if not rsi_series.dropna().empty else 50.0
            macd_val = macd.dropna().iloc[-1] if not macd.dropna().empty else 0.0
            signal_val = signal.dropna().iloc[-1] if not signal.dropna().empty else 0.0

            return round(rsi_val, 2), round(macd_val, 5), round(signal_val, 5)

        except Exception as e:
            print(f"❌ Fehler bei Indikatorberechnung: {e}")
            return 50.0, 0.0, 0.0  # Absolute Fallback-Werte

    def get_trading_decision(self, rsi: float, macd: float, signal: float, epic: str = None) -> str:
        if epic == "XRPUSD":
            if rsi < self.xrp_params["rsi_oversold"] and macd > signal * 0.8:
                return "BUY"
            elif rsi > self.xrp_params["rsi_overbought"] and macd < signal * 0.8:
                return "SELL"
            else:
                return "HOLD"
        else:
            if rsi < self.rsi_oversold and macd > signal * 0.8:
                return "BUY"
            elif rsi > self.rsi_overbought and macd < signal * 0.8:
                return "SELL"
            else:
                return "HOLD"

    def load_sl_tp_config(self, path="sl_tp_config.json"):
        try:
            with open(path, "r") as f:
                self.asset_params = json.load(f)
        except Exception as e:
            print(f"⚠️ Fehler beim Laden der SL/TP-Konfiguration: {e}")
            self.asset_params = {
                "default": {
                    "stop_loss_percent": 0.03,
                    "take_profit_percent": 0.05
                }
            }

    def calculate_stop_loss_take_profit(self, current_price: float, direction: str, epic: str) -> Tuple[float, float]:
        """
        Holt aktuelle SL/TP-Werte direkt von der lernfähigen SLTP-KI (sltp_manager).
        """
        params = self.sltp_manager.get_params(epic)
        sl_percent = params["stop_loss_percent"]
        tp_percent = params["take_profit_percent"]

        if direction == "BUY":
            stop_loss = current_price * (1 - sl_percent)
            take_profit = current_price * (1 + tp_percent)
        else:
            stop_loss = current_price * (1 + sl_percent)
            take_profit = current_price * (1 - tp_percent)

        return stop_loss, take_profit

    def get_valid_price_data(self, epic: str, limit: int = 100) -> Optional[list]:
        """
        Holt historische Preisreihe für ein Epic und prüft sie auf Gültigkeit.
        Gibt Liste von Preis-Einträgen oder None zurück.
        """
        try:
            price_data = self.api.get_price_history(epic, resolution="MINUTE", limit=limit)
            if price_data and "prices" in price_data:
                return price_data["prices"]
            else:
                print(f"⚠️ Ungültige oder leere Preisreihe für {epic}")
                return None
        except Exception as e:
            print(f"❌ Fehler beim Abruf historischer Preise für {epic}: {e}")
            return None

    def analyze_market(self, epic: str) -> Dict[str, Any]:
        """
        Führt eine vollständige Marktanalyse für ein Epic durch und liefert ggf. ein Signal.
        """
        try:
            market_info = self.api.get_market_info(epic)
            snapshot = market_info.get("snapshot", {})

            if not snapshot or "bid" not in snapshot:
                print(f"⚠️ Kein gültiger Preis für {epic}")
                return {}

            price = float(snapshot.get("bid", 0.0))
            if price <= 0:
                print(f"⚠️ Ungültiger Preis ({price}) – Mapping wird aktualisiert")
                update_epic_mapping([epic])
                return {}

            price_data = self.api.get_price_history(epic, resolution="MINUTE", limit=100)
            if not price_data or "prices" not in price_data:
                print(f"⚠️ Keine gültigen historischen Preisdaten für {epic}")
                return {}

            prices = [
                float(p["closePrice"]["bid"])
                for p in price_data["prices"]
                if isinstance(p.get("closePrice"), dict) and "bid" in p["closePrice"]
            ]

            if not prices:
                print(f"⚠️ Preisreihe leer für {epic}")
                return {}

            preise_series = pd.Series(prices)
            current_price = preise_series.iloc[-1]

            # Optional: Indikatoren berechnen (falls benötigt)
            rsi, macd, signal = self.calculate_indicators(preise_series)

            data = {
                "epic": epic,
                "price": current_price,
                "preise": preise_series.tolist(),
                "rsi": rsi,
                "macd": macd,
                "signal": signal
            }

            from strategie_engineV2 import ist_einstieg_geeignet, ermittle_richtung

            if ist_einstieg_geeignet(data):
                direction = ermittle_richtung(data)
                size = self.api.berechne_trade_groesse(epic)

                if size > 0:
                    print(f"✅ Einstieg erkannt für {epic} – Richtung: {direction}, Größe: {size}")
                    return {
                        "epic": epic,
                        "direction": direction,
                        "size": size
                    }
                else:
                    print(f"⚠️ Größe zu klein oder 0 für {epic}")
            else:
                print(f"⚠️ Kein Einstiegssignal für {epic}")

        except Exception as e:
            print(f"{Fore.RED}❌ Fehler bei Analyse für {epic}: {e}{Style.RESET_ALL}")

        return {}

    def analyze_all_positions(self) -> List[Dict[str, Any]]:
        self.trading_ki.lade_strategy_modus()
        self.trading_ki.automatischer_moduswechsel(performance=self.total_profit)
        signals = []
        whitelist = load_whitelist()
        trending_epics = [m["epic"] for m in self.get_tradeable_markets()]
        print(f"📈 Beobachtete Märkte: {trending_epics}")
        print(f"{Fore.BLUE}Strategiemodus: {self.trading_ki.strategy_mode}{Style.RESET_ALL}")

        for epic in trending_epics:
            try:
                name = whitelist.get(epic)
                if not name:
                    market_info = self.api.get_market_info(epic)
                    name = market_info.get("instrument", {}).get("name", "Unbekannt")
                    update_whitelist(epic, name)
                print(f"📌 {epic} = {name}")

                preis = self.price_manager.get_combined_price(epic)
                if preis is None:
                    print(f"⛔ Preis für {epic} konnte nicht ermittelt werden.")
                    continue

                tage = 30  # z. B. dynamisch aus Settings
                preise_series = self.price_manager.get_combined_price_series(epic)

                # ❗Robuste Prüfung:
                if preise_series is None or (hasattr(preise_series, "empty") and preise_series.empty):
                    print(f"⛔ Leere oder ungültige Preisreihe für {epic}")
                    continue

                # Optional: Falls Series → in DataFrame umwandeln mit 'close'
                if isinstance(preise_series, pd.Series):
                    preise_series = preise_series.to_frame(name="close")

                # Noch eine Absicherung:
                if "close" not in preise_series.columns:
                    print(f"⛔ Keine 'close'-Spalte in Preisreihe für {epic}")
                    continue

                preis = preise_series.iloc[-1]
                try:
                    rsi, macd, signal = self.calculate_indicators(preise_series)
                except Exception as e:
                    print(f"❌ Fehler bei Indikator-Berechnung für {epic}: {e}")
                    traceback.print_exc()
                    continue

                datenpaket = {
                    "epic": epic,
                    "preis": preis,
                    "preise": preise_series["close"].tolist(),
                    "macd": macd,
                    "signal": signal,
                    "rsi": rsi,
                    "support": preis - 1.5,
                    "volumen": 1000,
                    "volumen_schnitt": 800,
                    "nachrichten": ["Company beats expectations", "Stock upgrade by analyst"]
                }

                symbol_info = self.trading_ki.normalisiere_epic(epic)
                datenpaket["symbol_finnhub"] = symbol_info["finnhub"]
                datenpaket["symbol_yfinance"] = symbol_info["yfinance"]

                try:
                    raw_signal = self.trading_ki.generiere_signal(epic, datenpaket, self.capital)
                    if raw_signal:
                        print(f"✅ Signal generiert für {epic}")
                        signals.append(raw_signal)
                        for signal in self.trading_ki.get_latest_signals(5):
                            try:
                                clean_signal = {
                                    k: str(v) if isinstance(v, pd.DataFrame) else v
                                    for k, v in signal.items()
                                }
                                pprint.pprint(clean_signal)
                            except Exception as sig_err:
                                print(f"⚠️ Fehler beim Drucken des Signals: {sig_err}")

                        df = self.price_manager.get_combined_price_series(epic, days=7)
                        if df is None or df.empty:
                            print(f"⚠️ Kein Chart-DataFrame für {epic} verfügbar")
                            continue
                        if isinstance(df, pd.Series):
                            df = df.to_frame(name="close")
                        if "close" not in df.columns:
                            print(f"⚠️ 'close'-Spalte fehlt in df für {epic}")
                            continue

                        chart_info = self.chart_analyzer.analysiere_chartverlauf(df)
                        kombi_signal = self.chart_analyzer.kombiniere_mit_signal(raw_signal, chart_info)

                        if kombi_signal.get("confidence", 0) > 0.7 and kombi_signal.get("richtung") == "BUY":
                            self.open_position(kombi_signal)
                    else:
                        print(f"⚠️ Kein gültiges Signal für {epic}")
                except Exception as e:
                    print(f"❌ Fehler bei Signal-Analyse für {epic}: {e}")

            except Exception as outer_error:
                print(f"❌ Schwerwiegender Fehler bei {epic}: {outer_error}")
                traceback.print_exc()

        return signals

    def check_account_balance(self):
        """Kontostand vom API abrufen und anzeigen."""
        try:
            data = self.api.get_account_info()
            accounts = data.get("accounts", [])
            if accounts:
                konto = accounts[0]
                balance = konto.get("balance", {})
                print(f"📊 Kontostand: {balance.get('available', 0)} {balance.get('currency', '')}")
            else:
                print("⚠️ Keine Kontoinformationen gefunden.")
        except Exception as e:
            print(f"{Fore.RED}❌ Fehler beim Abrufen des Kontostands: {e}{Style.RESET_ALL}")

    def check_kapitalfreigabe(self):
        """Prüft, ob der Zielplan einen Eintrag für heute hat."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            zielplan = pd.read_csv("zielplan.csv")

            if today not in zielplan["Datum"].values:
                print(f"{Fore.RED}❌ Kein Zielplan-Eintrag für heute ({today}) gefunden!{Style.RESET_ALL}")
                self.running = False
                return

            zielwert = zielplan.loc[zielplan["Datum"] == today, "Zielbetrag"].values[0]
            if zielwert <= 0:
                print(f"{Fore.RED}❌ Zielbetrag für heute = 0 – Trading wird gestoppt!{Style.RESET_ALL}")
                self.running = False
                return

            print(f"{Fore.GREEN}✅ Kapitalfreigabe OK: Tagesziel = {zielwert:.2f} CHF{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}❌ Fehler beim Lesen des Zielplans: {e}{Style.RESET_ALL}")
            self.running = False

    def berechne_kapitalaufteilung(self):
        """Berechnet die Kapitalaufteilung für Daytrading & Langfrist-Invest."""
        try:
            konto = self.api.get_account_info()
            balance = konto.get("accounts", [{}])[0].get("balance", {})
            verfuegbar = balance.get("available", 0)

            aktiv_kapital = verfuegbar * (2 / 3)
            day_kapital = aktiv_kapital * 0.8
            long_kapital = aktiv_kapital * 0.2

            print(f"{Fore.CYAN}💰 Verfügbares Kapital (API): {verfuegbar:.2f} CHF{Style.RESET_ALL}")
            print(f"{Fore.CYAN}➡️ Aktiv nutzbares Kapital (2⁄3): {aktiv_kapital:.2f} CHF{Style.RESET_ALL}")
            print(f"{Fore.CYAN}    ▪️ Daytrading-Kapital (80 %): {day_kapital:.2f} CHF{Style.RESET_ALL}")
            print(f"{Fore.CYAN}    ▪️ Langfrist-Kapital (20 %): {long_kapital:.2f} CHF{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}❌ Fehler bei der Kapitalberechnung: {e}{Style.RESET_ALL}")

    def print_performance_report(self):
        ziel = berechne_zielbereiche()
        take_profit_pct = ziel["take_profit_pct"]
        stop_loss_pct = ziel["stop_loss_pct"]
        """Druckt jede Stunde eine kleine Zusammenfassung."""
        current_time = datetime.now()
        if (current_time - self.last_hour_check).total_seconds() >= 3600:
            win_rate = (self.winning_trades / self.positions_closed * 100) if self.positions_closed > 0 else 0

            print(f"\n{Fore.MAGENTA}=== PERFORMANCE-ÜBERSICHT (STÜNDLICH) ==={Style.RESET_ALL}")
            print(
                f"Stündlicher Gewinn: {Fore.GREEN if self.hourly_profit >= 0 else Fore.RED}{self.hourly_profit:.2f} CHF{Style.RESET_ALL}")
            print(
                f"Gesamtgewinn: {Fore.GREEN if self.total_profit >= 0 else Fore.RED}{self.total_profit:.2f} CHF{Style.RESET_ALL}")
            print(f"Gewinnrate: {Fore.GREEN if win_rate >= 50 else Fore.RED}{win_rate:.2f}%{Style.RESET_ALL}")
            print(f"Offene Trades: {self.positions_opened - self.positions_closed}")
            print("=========================================\n")

            # Zurücksetzen für nächste Stunde
            self.hourly_profit = 0.0
            self.last_hour_check = current_time

    def open_position(self, signal: Dict[str, Any]):
        """Öffnet eine Position auf Basis eines KI-Signals – inkl. SL/TP, Logging, Sound & Memory."""
        ziel = berechne_zielbereiche()
        take_profit_pct = ziel.get("take_profit_pct", 1.5)
        stop_loss_pct = ziel.get("stop_loss_pct", 1.0)

        if not self.live_mode:
            print(f"{Fore.YELLOW}🔒 Live-Trading ist deaktiviert. Order wird nicht gesendet.{Style.RESET_ALL}")
            return

        epic = signal.get("epic")
        direction = signal.get("direction")
        confidence = signal.get("confidence", 0.0)
        dauer = signal.get("dauer", 3)
        risiko = signal.get("risiko", "MITTEL")

        # 🧮 Tradegröße berechnen oder übernehmen
        größe_result = signal.get("size")
        if not größe_result:
            größe_result = self.api.berechne_trade_groesse(epic)
        if isinstance(größe_result, dict):
            size = größe_result.get("anzahl", 0.0)
            preis = größe_result.get("preis", "?")
            min_deal_size = größe_result.get("min_deal_size", "?")
            self.trading_ki.memory.speichere(epic, {"order_details": größe_result})
        else:
            size = größe_result
            preis = "?"
            min_deal_size = "?"

        if size == 0.0:
            print(f"{Fore.RED}⚠️ Keine gültige Tradegröße für {epic}. Order wird abgebrochen.{Style.RESET_ALL}")
            return

        print(
            f"📤 Sende Order: {epic} → {direction} | Größe: {size:.2f} | Preis: {preis} | Conf: {confidence:.2f} | Dauer: {dauer}min | Risiko: {risiko}")

        try:
            # ✅ Mindestgröße prüfen
            markt_info = self.api.get_market_info(epic)
            min_unit = float(markt_info.get("minDealSize", 1))
            if not self.api.pruefe_mindestgroesse(epic, size, min_unit):
                print(f"{Fore.YELLOW}⚠️ Größe unter Mindestgröße. Order abgebrochen.{Style.RESET_ALL}")
                return

            # ✅ Bereits offene Position prüfen
            positions = self.api.get_positions()
            already_open = any(p.get("epic") == epic for p in positions.get("positions", []))
            if already_open:
                print(f"{Fore.YELLOW}⚠️ Position für {epic} bereits offen.{Style.RESET_ALL}")
                return

            # 📈 Preisverlauf abrufen (für SL/TP)
            price_data = self.api.get_price_history(epic, resolution="MINUTE", limit=100)
            if not price_data or "prices" not in price_data:
                print(f"⚠️ Keine Preisdaten für {epic} – SL/TP kann nicht berechnet werden.")
                return

            prices = [
                float(p["closePrice"]["bid"])
                for p in price_data["prices"]
                if isinstance(p.get("closePrice"), dict) and "bid" in p["closePrice"]
            ]
            if not prices:
                print(f"{Fore.RED}❌ Keine gültigen Preisdaten für {epic}.{Style.RESET_ALL}")
                return

            current_price = prices[-1]
            stop_loss, take_profit = self.calculate_stop_loss_take_profit(current_price, direction, epic)

            # ✅ Order senden
            result = self.api.place_order(
                epic=epic,
                direction=direction,
                size=size,
                stop_loss=stop_loss,
                take_profit=take_profit
            )

            if result:
                print(
                    f"{Fore.GREEN}✅ Position geöffnet: {epic} ({direction}) | SL: {stop_loss:.2f}, TP: {take_profit:.2f}{Style.RESET_ALL}")

                # 🧠 Memory speichern
                self.trading_ki.memory.speichere_signal(epic, {
                    "zeit": datetime.now().isoformat(),
                    "richtung": direction,
                    "preis": current_price,
                    "groesse": size,
                    "confidence": confidence,
                    "risiko": risiko,
                    "dauer": dauer
                })

                # 🖥 UI + Ton
                popup_nachricht("📈 Neues Signal", f"{epic} → {direction} ({confidence * 100:.0f}%)")
                spiele_ton()

                # 📘 Logging
                self.logge_gewinn(epic, 0.0, confidence, risiko, dauer)

                # 📊 Trades verwalten
                self.positions_opened += 1
                self.active_trades[epic] = {
                    "entry_time": datetime.now(),
                    "entry_price": current_price,
                    "position_size": size,
                    "direction": direction,
                    "confidence": confidence,
                    "dauer": dauer,
                    "risiko": risiko,
                }
            else:
                print(f"{Fore.RED}❌ Order für {epic} konnte nicht platziert werden.{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}🔥 Fehler beim Öffnen der Position: {e}{Style.RESET_ALL}")

    def feedback_nach_trade(self, epic: str, signal: dict, preis: float):
        """
        Übergibt nach erfolgreicher Order ein Feedback an die KI.
        """
        try:
            self.trading_ki.memory.speichere(epic, {
                "typ": "order_feedback",
                "zeit": datetime.now().isoformat(),
                "preis": preis,
                "richtung": signal.get("direction"),
                "groesse": signal.get("size"),
                "confidence": signal.get("confidence"),
                "risiko": signal.get("risiko"),
                "dauer": signal.get("dauer")
            })
            print(f"🧠 KI-Rückmeldung gespeichert für {epic}")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Rückmeldung an KI fehlgeschlagen: {e}{Style.RESET_ALL}")

    def logge_gewinn(self, epic: str, gewinn: float, confidence: float, risiko: float, dauer: int):
        """Loggt das Ergebnis eines abgeschlossenen Trades in Memory & CSV."""
        from memory_module import MemoryModule

        memory = MemoryModule()
        eintrag = {
            "zeit": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "gewinn": gewinn,
            "confidence": confidence,
            "risiko": risiko,
            "dauer": dauer,
        }
        memory.speichere_signal(epic, eintrag)

        # Zusätzlich: CSV-Logging
        logzeile = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')};{epic};{gewinn:.2f};{confidence:.2f};{risiko if isinstance(risiko, str) else f'{risiko:.2f}'};{dauer}\n"
        try:
            with open("guv_log.csv", "a") as f:
                f.write(logzeile)
        except Exception as e:
            print(f"{Fore.RED}❌ Fehler beim Schreiben in guv_log.csv: {e}{Style.RESET_ALL}")

    def check_open_positions(self):
        """Durchläuft alle offenen Positionen und analysiert sie."""
        try:
            positions = self.api.get_positions()
            all_positions = positions.get("positions", [])

            if not all_positions:
                return

            for position in all_positions:
                try:
                    epic = position.get("epic")
                    if not epic:
                        continue

                    position_id = position.get("dealId")
                    if not position_id:
                        print(f"⚠️ Ungültige Position (kein Deal-ID): {position}")
                        continue

                    direction = position.get("direction")
                    current_profit = float(position.get("profit", 0))

                    price_history = self.api.get_price_history(epic, resolution="MINUTE", limit=100)
                    print("🔍 Preisdaten-Vorschau:", price_history)
                    prices = []
                    for p in price_history.get("prices", []):
                        if isinstance(p, dict):
                            cp = p.get("closePrice")
                            if isinstance(cp, dict):
                                bid = cp.get("bid")
                                if isinstance(bid, (int, float)):
                                    prices.append(float(bid))
                    prices = pd.Series(prices)
                    if prices.empty:
                        continue

                    rsi, macd, macd_signal = self.calculate_indicators(prices)

                    trade_info = self.active_trades.get(epic, {})
                    confidence = trade_info.get("confidence", 0.0)
                    risiko = trade_info.get("risiko", 0.0)
                    dauer = trade_info.get("dauer", 0)

                    if direction == "SELL" and (rsi < 20 or macd < macd_signal * 0.8) and current_profit > 0:
                        self.api.close_position(position_id)
                        self.update_trade_stats(current_profit)
                        self.add_trade_to_history(epic, "SHORT", current_profit)
                        self.logge_gewinn(epic, current_profit, confidence, risiko, dauer)

                        eintrag = self.active_trades.get(epic, {})
                        entry_time = eintrag.get("entry_time", datetime.now())
                        dauer = (datetime.now() - entry_time).seconds // 60
                        confidence = eintrag.get("confidence", 0.0)
                        risiko = eintrag.get("risiko", 0.0)

                        self.trading_ki.verarbeite_trade_resultat(epic, {
                            "gewinn": current_profit,
                            "dauer": dauer,
                            "confidence": confidence,
                            "risiko": risiko
                        })

                        from guv_checker import GUVChecker
                        checker = GUVChecker()
                        checker.berechne_guv(self.berechne_aktuellen_gewinn())

                    elif direction == "BUY" and (rsi > 80 or macd > macd_signal * 0.8) and current_profit > 0:
                        self.api.close_position(position_id)
                        self.update_trade_stats(current_profit)
                        self.add_trade_to_history(epic, "LONG", current_profit)
                        self.logge_gewinn(epic, current_profit, confidence, risiko, dauer)

                        eintrag = self.active_trades.get(epic, {})
                        entry_time = eintrag.get("entry_time", datetime.now())
                        dauer = (datetime.now() - entry_time).seconds // 60
                        confidence = eintrag.get("confidence", 0.0)
                        risiko = eintrag.get("risiko", 0.0)

                        self.trading_ki.verarbeite_trade_resultat(epic, {
                            "gewinn": current_profit,
                            "dauer": dauer,
                            "confidence": confidence,
                            "risiko": risiko
                        })

                except Exception as e:
                    print(f"⚠️ Fehler beim Verarbeiten der Position: {e}")
                    continue

        except Exception as e:
            print(f"{Fore.RED}⚠️ Fehler bei check_open_positions: {e}{Style.RESET_ALL}")

    def longterm_invest(self):
        """Simulierte Longterm-Investments (später durch echten Kauf ersetzbar)."""
        portfolio = {
            "ETF_SP500": 0.4,
            "ETF_Nasdaq": 0.3,
            "Gold_ETF": 0.2,
            "GreenEnergy_ETF": 0.1
        }

        longterm_capital = self.capital * 0.2
        print(f"{Fore.CYAN}📈 Starte langfristige Investments mit {longterm_capital:.2f} CHF...{Style.RESET_ALL}")

        for asset, weight in portfolio.items():
            amount = longterm_capital * weight
            print(f"{Fore.GREEN}💸 Investiere {amount:.2f} CHF in {asset}{Style.RESET_ALL}")
            try:
                self.api.place_longterm_investment(asset, amount)
            except Exception as e:
                print(f"{Fore.RED}❌ Fehler beim Investieren in {asset}: {e}{Style.RESET_ALL}")

    def update_trade_stats(self, profit: float):
        """Aktualisiert die Performance-Statistiken."""
        self.total_profit += profit
        self.hourly_profit += profit
        self.positions_closed += 1

        if profit > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

    def toggle_aggression(self):
        new_state = self.switch_var.get()
        self.set_aggressiveness(new_state)
        self.status_label.config(text=self.status_text())

    def status_text(self):
        return "Modus: AGGRESSIV" if self.switch_var.get() else "Modus: DEFENSIV"

    def set_aggressiveness(self, aggressive: bool):
        """
        Setzt den Modus (aggressiv oder defensiv).
        """
        self.aggressive_mode = aggressive

    def backtest_modus(self, epic_liste: List[str], tage: int = 30):
        """
        Führt einen Backtest durch auf Basis der letzten Tage.
        """
        for epic in epic_liste:
            print(f"\n⏮ Backtest für {epic} gestartet ({tage} Tage)")

            try:
                df = self.price_manager.get_combined_price_series(epic, days=tage)

                # Absicherung gegen None oder leeren Series/DataFrame
                if df is None:
                    print(f"❌ Kein DataFrame für {epic} – df ist None")
                    continue

                if isinstance(df, pd.Series):
                    df = df.to_frame(name="close")
                    print(f"🔄 Series wurde zu DataFrame mit 'close'-Spalte umgewandelt")

                if df.empty:
                    print(f"❌ DataFrame für {epic} ist leer")
                    continue

                # Spaltennamen normalisieren (z. B. Close → close)
                for col in df.columns:
                    if col.lower() == "close":
                        df = df.rename(columns={col: "close"})
                        print(f"🔄 Spalte '{col}' → 'close' normalisiert")
                        break

                if "close" not in df.columns:
                    print(f"⛔ 'close'-Spalte fehlt für {epic} – kann nicht fortfahren")
                    continue

                print(f"✅ Daten geladen für {epic}: {len(df)} Zeilen")
                print(df.head(2))

                # Chartanalyse ausführen
                chart_info = self.chart_analyzer.analysiere_chartverlauf(df)
                print(f"📊 Analyse-Ergebnis für {epic}: {chart_info}")

                # Datenpaket für KI
                datenpaket = {
                    "epic": epic,
                    "preise": df["close"].tolist(),
                    "nachrichten": ["Backtest scenario"],
                    "macd": 0,
                    "rsi": 50,
                    "volumen": 1000,
                    "volumen_schnitt": 900,
                    "symbol_finnhub": self.trading_ki.normalisiere_epic(epic).get("finnhub"),
                    "symbol_yfinance": self.trading_ki.normalisiere_epic(epic).get("yfinance"),
                }

                # KI-Signal erzeugen
                signal = self.trading_ki.generiere_signal(epic, datenpaket, kapital=self.capital)

                if signal:
                    print(f"✅ Backtest-Signal für {epic}: {signal}")
                else:
                    print(f"⚠️ Kein gültiges Signal im Backtest für {epic}")

            except Exception as e:
                print(f"{Fore.RED}❌ Fehler im Backtest für {epic}: {e}{Style.RESET_ALL}")

    def run(self):
        print(f"🟢 Trading-Bot gestartet um {datetime.now().strftime('%H:%M:%S')}")
        self.check_account_balance()
        self.check_kapitalfreigabe()
        self.berechne_kapitalaufteilung()

        if not self.running:
            print(f"{Fore.RED}❌ Bot-Start gestoppt – Zielplan ungültig oder Kapital = 0{Style.RESET_ALL}")
            return

        time.sleep(0.1)

        while self.running:
            try:
                self.check_margin()

                signals = self.analyze_all_positions()
                print(f"📩 Empfangene Signale: {len(signals)}")

                # 🔐 Sicherheitsblock für Signalausgabe
                for s in signals:
                    try:
                        epic = s.get("epic", "???")
                        richtung = s.get("direction", "???")
                        confidence = s.get("confidence", 0.0)
                        print(f"📈 Signal: {epic} → {richtung} ({confidence * 100:.1f}%)")
                    except Exception as sig_err:
                        print(f"{Fore.YELLOW}⚠️ Fehler beim Signalausdruck: {sig_err}{Style.RESET_ALL}")
                        continue

                for signal in signals:
                    try:
                        print(f"📤 Debug-Signal: {json.dumps(signal, indent=2)}")
                        self.open_position(signal)
                    except Exception as e:
                        print(f"{Fore.RED}❌ Fehler bei open_position: {e}{Style.RESET_ALL}")
                        continue

                try:
                    self.check_open_positions()
                    self.print_performance_report()
                except Exception as e:
                    print(f"{Fore.RED}⚠️ Fehler bei Positions-/Performance-Check: {e}{Style.RESET_ALL}")

                try:
                    from guv_visualizer import zeige_guv_verlauf
                    zeige_guv_verlauf()
                except Exception as e:
                    print(f"{Fore.YELLOW}⚠️ Fehler beim GUV-Visualizer: {e}{Style.RESET_ALL}")

                # Statusanzeige alle X Sekunden
                current_time = datetime.now()
                if (current_time - self.last_status_update).total_seconds() >= self.status_update_interval:
                    try:
                        self.print_status()
                        self.last_status_update = current_time
                    except Exception as e:
                        print(f"{Fore.YELLOW}⚠️ Fehler bei Statusanzeige: {e}{Style.RESET_ALL}")

            except Exception as e:
                print(f"{Fore.RED}⚠️ Fehler im Bot-Loop: {e}{Style.RESET_ALL}")
                time.sleep(self.analysis_interval)

    def get_tradeable_markets(self) -> List[Dict]:
        """Gibt die Liste der Märkte zurück, die aktuell beobachtet werden."""
        return self.markets

    def check_zielStatus(self):
        kontrolle = ZielKontrolle("zielplan.csv")
        ziel = kontrolle.heutiges_ziel()
        pnl = self.berechne_aktuellen_gewinn()  # Methode folgt gleich

        if pnl is None or ziel is None:
            print("⚠️ Ziel oder Gewinn konnte nicht berechnet werden.")
            return

        if pnl >= ziel:
            print(f"{Fore.GREEN}✅ Ziel erreicht! ({pnl:.2f} CHF / Ziel: {ziel:.2f} CHF){Style.RESET_ALL}")
        elif pnl >= 0:
            print(f"{Fore.YELLOW}🟡 Ziel noch nicht erreicht ({pnl:.2f} CHF / Ziel: {ziel:.2f} CHF){Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}🔴 Negativer Gewinn ({pnl:.2f} CHF / Ziel: {ziel:.2f} CHF){Style.RESET_ALL}")

    def berechne_aktuellen_gewinn(self) -> float:
        try:
            positionen = self.api.get_positions().get("positions", [])
            gewinn = sum([float(p.get("profit", 0.0)) for p in positionen])
            print(f"📊 Aktueller Gesamtgewinn (PnL): {gewinn:.2f} CHF")
            return gewinn
        except Exception as e:
            print(f"{Fore.RED}❌ Fehler bei Gewinnberechnung: {e}{Style.RESET_ALL}")
            return 0.0

    def exportiere_dashboard_status(self, pfad: str = "status_panel.json"):
        status = {
            "zeit": datetime.now().isoformat(),
            "modus": self.trading_ki.strategy_mode,
            "equity": self.total_equity,
            "margin": {
                "verfuegbar": self.available_margin,
                "genutzt": self.used_margin
            },
            "profit": {
                "gesamt": self.total_profit,
                "stunde": self.hourly_profit,
                "pnl_ratio": self.pnl_ratio
            },
            "trades": {
                "gewinn": self.winning_trades,
                "verlust": self.losing_trades,
                "rate": round((self.winning_trades / self.positions_closed) * 100, 2)
                if self.positions_closed > 0 else 0
            },
            "signale": self.trading_ki.signals[-5:]
        }

        try:
            with open(pfad, "w") as f:
                json.dump(status, f, indent=2)
            print(f"💾 Dashboard-Status exportiert nach {pfad}")
        except Exception as e:
            print(f"❌ Fehler beim Schreiben von {pfad}: {e}")



    def attach_gui(self, gui):
        self.switch_var = gui.switch_var
        self.status_label = gui.status_label

        # === ⏯️ PROGRAMMSTART ===

if __name__ == "__main__":
    from gui.aggression_control import AggressionControlGUI
    import threading

    API_KEY = "paDdIqX7rYuVi5g3"
    ACCOUNT_ID = "stefankobel90@outlook.com"
    PASSWORD = "Roxanne90?!"

    try:
        api = CapitalComAPI(API_KEY, ACCOUNT_ID, PASSWORD, use_demo=True)

        # Konfiguriere den Bot
        capital = 1000  # Gesamtbudget (CHF)
        position_size = 0.5
        aggressive_mode = False

        bot = TradingBotV4(api, capital, position_size, aggressive_mode)
        bot.live_mode = True

        # ✅ Wenn du live handeln willst, einfach True setzen:
        # bot.live_mode = True

        # Starte Bot im Hintergrund-Thread
        bot_thread = threading.Thread(target=bot.run)
        bot_thread.start()

        # Starte Aggressions-GUI im Hauptthread (Pflicht unter macOS)
        gui = AggressionControlGUI()
        gui.attach_bot(bot)
        bot.attach_gui(gui)

        # === 🧠 Manuelles Lern-Interface ===
        while True:
            befehl = input("📚 Lernbefehl (text/url/exit): ").strip().lower()

            if befehl == "exit":
                break

            elif befehl == "text":
                text = input("📝 Gib den Lerntext ein: ")
                bot.trading_ki.lerne_aus_text(text, quelle="CLI")

            elif befehl == "url":
                url = input("🌍 Gib die URL ein: ")
                bot.trading_ki.lerne_von_webseite(url)

            elif befehl == "show":
                bot.trading_ki.zeige_lernverlauf("lerntext")

            elif befehl == "auto":
                bot.trading_ki.lerninterface.autodurchlauf(bot.trading_ki)

            elif befehl == "analyse":
                text = input("🔍 Text für Analyse: ")
                analyse = bot.trading_ki.lerninterface.analysiere_text(text)
                print(analyse)

            elif befehl == "ordner":
                pfad = input("📁 Ordnerpfad: ")
                bot.trading_ki.lerne_aus_ordner(pfad)

            else:
                print("❌ Ungültiger Befehl. Bitte nutze: text / url / exit")

    except Exception as e:
        print(f"{Fore.RED}❌ Fehler beim Start: {e}{Style.RESET_ALL}")


    def print_epic_status(self, epic: str):
        print(f"\n{Fore.CYAN}=== STATUS FÜR {epic} ==={Style.RESET_ALL}")

        # Strategie-Modus anzeigen
        modus = self.trading_ki.strategy_mode
        print(f"{Fore.MAGENTA}Strategie-Modus: {modus}{Style.RESET_ALL}")

        # Letztes KI-Signal
        signal = self.trading_ki.gib_signal(epic)
        if signal:
            print(
                f"📩 Letztes Signal: {signal['direction']} (Conf: {signal['confidence']}, Risiko: {signal.get('risiko', '?')})")
        else:
            print("⚠️ Kein Signal vorhanden.")

        # Memory-Einträge
        self.trading_ki.auswertung_memory(epic)

        # News-Sentiment
        score = self.trading_ki.news_ki.analysiere_nachrichten(epic, [])
        print(f"📰 News-Score: {score:.2f}")

        print("────────────────────────────")


    def zeige_dashboard(self):
        self.clear_screen()
        self.print_status()

        print(f"{Fore.YELLOW}=== AKTUELLE SIGNALE ==={Style.RESET_ALL}")
        for signal in self.signals[-5:]:
            epic = signal.get("epic", "n/a")
            richtung = signal.get("direction", "n/a")
            confidence = signal.get("confidence", 0.0)
            print(f"📈 {epic}: {richtung} | Confidence: {confidence:.2f}")

        print(f"\n{Fore.YELLOW}=== STRATEGIEMODUS ==={Style.RESET_ALL}")
        print(f"Modus: {Fore.CYAN}{self.trading_ki.strategy_mode}{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}=== GELERNTE DATEN (Memory) ==={Style.RESET_ALL}")
        eintraege = self.trading_ki.memory.zeige_verlauf("lerntext")
        for eintrag in eintraege[-3:]:
            quelle = eintrag.get("quelle", "unbekannt")
            analyse = eintrag.get("analyse", {})
            print(f"🧠 Quelle: {quelle} | Analyse: {analyse}")


    def start_dashboard_loop(self):
        import time
        import threading

        def loop():
            while True:
                self.zeige_dashboard()
                time.sleep(self.status_update_interval)

        threading.Thread(target=loop, daemon=True).start()