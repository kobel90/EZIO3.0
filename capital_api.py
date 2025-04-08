import requests
import time
import threading
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from colorama import Fore, Style
import json
from utils.session_manager import SessionManager

# === Logging-Konfiguration ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CapitalComAPI:
    def __init__(self, api_key: str, account_id: str, password: str, use_demo: bool = True):
        self.API_KEY = api_key
        self.ACCOUNT_ID = account_id
        self.PASSWORD = password

        # 🌐 Basis-URL je nach Modus (Demo oder Live)
        self.BASE_URL = (
            "https://demo-api-capital.backend-capital.com"
            if use_demo else
            "https://api-capital.backend-capital.com"
        )

        self.session = requests.Session()
        self.session_manager = SessionManager(session_timeout_minutes=60)

        self.cst: Optional[str] = None
        self.security_token: Optional[str] = None
        self.session_active = threading.Event()
        self.session_thread: Optional[threading.Thread] = None

        self.last_request_time = datetime.now()
        self.request_count = 0
        self.request_window_start = datetime.now()

        self.MAX_REQUESTS_PER_SECOND = 10
        self.MAX_SESSION_REQUESTS_PER_SECOND = 1

        # Neue Zeile: Session starten (→ erhält Token!)
        print(
            f"🧠 Session gültig? → {self.session_manager.is_session_valid()} (Letzter Start: {self.session_manager.last_session_time})")
        if not self.session_manager.is_session_valid():
            self.start_session()

        if self.session_manager.last_session_time:
            remaining = self.session_manager.last_session_time + self.session_manager.timeout - datetime.now()
            print(f"⏳ Noch gültig für: {remaining}")

    def _wait_for_rate_limit(self, is_session_request: bool = False) -> None:
        current_time = datetime.now()
        if is_session_request:
            time_since_last = (current_time - self.last_request_time).total_seconds()
            if time_since_last < 1.0:
                time.sleep(1.0 - time_since_last)
        else:
            if self.request_count >= self.MAX_REQUESTS_PER_SECOND:
                time_since_window = (current_time - self.request_window_start).total_seconds()
                if time_since_window < 1.0:
                    time.sleep(1.0 - time_since_window)
                self.request_count = 0
                self.request_window_start = datetime.now()
        self.last_request_time = datetime.now()
        self.request_count += 1

    def place_order(self, epic: str, direction: str, size: float,
                    stop_loss: Optional[float] = None,
                    take_profit: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Führt eine Order aus und gibt die API-Antwort zurück (oder None bei Fehler).
        """
        if not self.cst or not self.security_token:
            logger.warning("⚠️ Nicht authentifiziert. Order wird nicht gesendet.")
            return None

        order_payload = {
            "epic": epic,
            "direction": direction,
            "size": str(size),
            "orderType": "MARKET",
            "currencyCode": "USD",
            "guaranteedStop": False,
            "forceOpen": True,
            "stopLevel": str(round(stop_loss, 4)) if stop_loss else None,
            "profitLevel": str(round(take_profit, 4)) if take_profit else None
        }
        order_payload = {k: v for k, v in order_payload.items() if v is not None}
        endpoint = "/api/v1/positions"

        response = self.send_request("POST", endpoint, data=order_payload)

        if response and response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.error("❌ JSON-Fehler bei Order-Antwort.")
                return None
        else:
            logger.error(f"❌ Order fehlgeschlagen – Status: {response.status_code if response else 'keine Antwort'}")
            return None

    def send_request(self, method: str, endpoint: str,
                     data: Optional[dict] = None,
                     params: Optional[dict] = None) -> Optional[requests.Response]:
        """
        Zentraler Request-Wrapper – funktioniert für alle HTTP-Methoden (GET, POST, DELETE)
        """
        return self.send_http_request(method, endpoint, data=data, params=params)
    def send_http_request(self, method: str, endpoint: str, data=None, params=None, headers=None, timeout=5) -> \
    Optional[requests.Response]:
        url = f"{self.BASE_URL}{endpoint}"
        headers = headers or self.get_headers()
        retry_count = 3

        for attempt in range(1, retry_count + 1):
            self._wait_for_rate_limit()

            try:
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                    timeout=timeout
                )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 60
                    logger.warning(f"🛑 API-Limit (429) – Warte {wait_time} Sekunden (Versuch {attempt}/{retry_count})")
                    time.sleep(wait_time)
                    continue

                if response.status_code in [401, 403] and self.reauth_if_needed(response):
                    logger.info(f"🔁 Reauth erfolgreich – wiederhole Anfrage (Versuch {attempt}/{retry_count})")
                    continue

                if response.status_code >= 400:
                    logger.error(f"❌ HTTP-Fehler {method.upper()} {url} ({response.status_code}): {response.text}")
                else:
                    return response

            except requests.exceptions.RequestException as e:
                logger.error(f"⚠️ Anfrage fehlgeschlagen ({method.upper()} {url}): {e}")

        logger.critical("❗ Max. Wiederholungen erreicht – Anfrage fehlgeschlagen.")
        return None

    def reauth_if_needed(self, response: requests.Response) -> bool:
        """
        Erkennt ungültige Session (401/403) und versucht Re-Authentifizierung.
        Gibt True zurück, wenn eine neue Session erfolgreich gestartet wurde.
        """
        if response.status_code in [401, 403]:
            logger.warning(f"🔐 Ungültige Session erkannt ({response.status_code}) → Versuche Reauth...")
            try:
                self.start_session()
                return True
            except Exception as e:
                logger.critical(f"❌ Reauthentifizierung fehlgeschlagen: {e}")
        return False

    def get_headers(self) -> Dict[str, str]:
        headers = {
            "X-CAP-API-KEY": self.API_KEY,
            "Content-Type": "application/json"
        }
        if self.cst:
            headers["CST"] = self.cst
        if self.security_token:
            headers["X-SECURITY-TOKEN"] = self.security_token
        return headers

    def authenticate(self) -> bool:
        try:
            print(f"{Fore.CYAN}Versuche API-Authentifizierung...{Style.RESET_ALL}")
            response = requests.post(
                f"{self.BASE_URL}/api/v1/session",
                headers={"X-CAP-API-KEY": self.API_KEY, "Content-Type": "application/json"},
                json={"identifier": self.ACCOUNT_ID, "password": self.PASSWORD}
            )
            if response.status_code == 200:
                self.cst = response.headers.get("CST")
                self.security_token = response.headers.get("X-SECURITY-TOKEN")
                if not self.cst or not self.security_token:
                    raise Exception("Authentifizierung fehlgeschlagen: Keine Token erhalten")
                print(f"{Fore.GREEN}API-Authentifizierung erfolgreich!{Style.RESET_ALL}")
                return True
            else:
                raise Exception(f"Fehler {response.status_code}: {response.text}")
        except Exception as e:
            print(f"{Fore.RED}Fehler bei der API-Authentifizierung: {str(e)}{Style.RESET_ALL}")
            raise

    def start_session(self):
        if self.session_active.is_set():
            print("⚠️ Session bereits aktiv – kein erneuter Aufbau.")
            return
        print(f"🔄 Starte neue Session... (Zeit: {datetime.now().strftime('%H:%M:%S')})")
        """Startet eine neue API-Session und gibt Tokens aus"""
        url = f"{self.BASE_URL}/api/v1/session"
        headers = {
            "X-CAP-API-KEY": self.API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "identifier": "stefankobel90@outlook.com",
            "password": self.PASSWORD,
            "encryptedPassword": False
        }

        print("🛰 Finaler POST-Test:")
        print("🔐 API-Key:", repr(self.API_KEY))
        print("📧 Identifier:", repr(payload["identifier"]))
        print("🔑 Password:", repr(payload["password"]))

        print("🛰 URL:", url)
        print("📦 Payload:", payload)
        print("🧾 Header:", headers)
        response = self.session.post(
            url,
            headers=headers,
            data=json.dumps(payload)  # explizit als JSON-String senden
        )
        response.raise_for_status()  # <- genau hier kommt dein 400er, wenn was nicht stimmt

        self.cst = response.headers.get("CST")
        self.security_token = response.headers.get("X-SECURITY-TOKEN")
        print(f"✅ API-Session gestartet – CST: {self.cst}, Token: {self.security_token}")

        self.session_manager.mark_session_start()
        print(f"✅ Session gestartet – CST: {self.cst[:6]}... | Token: {self.security_token[:6]}...")


    def get_account_info(self) -> Dict[str, Any]:
        """
        Holt vollständige Account-Informationen (Kontostände, Währungen, Margins).
        Gibt ein Dictionary mit allen Accounts zurück oder ein leeres Dict bei Fehlern.
        """
        if not self.cst or not self.security_token:
            logger.warning("⚠️ Nicht authentifiziert. get_account_info() abgebrochen.")
            return {}

        response = self.send_request("GET", "/api/v1/accounts")

        if response is None:
            logger.error("❌ Keine Antwort bei get_account_info() – API vermutlich blockiert.")
            return {}

        try:
            response.raise_for_status()
            data = response.json()
            logger.info("📊 Accountinformationen erfolgreich abgerufen.")
            return data

        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP-Fehler bei get_account_info(): {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Verbindungsfehler bei get_account_info(): {e}")
        except Exception as e:
            logger.exception(f"❌ Unerwarteter Fehler in get_account_info(): {e}")

        return {}

    def get_price_history(self, epic: str, resolution: str = "MINUTE", limit: int = 100, debug: bool = False) -> Dict:
        """
        Ruft Preisverlauf für ein EPIC ab – nutzt zentralen Wrapper mit Retry.
        """
        if not self.cst or not self.security_token:
            logger.warning("⚠️ Nicht authentifiziert. get_price_history() abgebrochen.")
            return {}

        endpoint = f"/api/v1/prices/{epic}"
        params = {"resolution": resolution, "max": limit}

        response = self.send_request("GET", endpoint, params=params)

        if response and response.status_code == 200:
            try:
                data = response.json()
                if debug:
                    logger.debug(f"🔍 [DEBUG] Preisdaten für {epic}:\n{json.dumps(data, indent=2)}")
                return data
            except json.JSONDecodeError:
                logger.error(f"❌ JSON-Fehler bei Preisdaten {epic}")
        else:
            logger.warning(f"⚠️ Keine gültige Antwort für Preisverlauf {epic}")

        return {}

    def get_market_info(self, epic: str) -> Dict[str, Any]:
        """
        Holt Marktinformationen zu einem EPIC.
        """
        if not self.cst or not self.security_token:
            logger.warning("⚠️ Nicht authentifiziert. get_market_info() abgebrochen.")
            return {}

        endpoint = f"/api/v1/markets/{epic}"
        response = self.send_request("GET", endpoint)

        if response and response.status_code == 200:
            try:
                data = response.json()
                logger.debug(f"ℹ️ Marktinfo {epic}: {json.dumps(data, indent=2)}")
                return data
            except json.JSONDecodeError:
                logger.error(f"❌ JSON-Fehler bei Marktinfo {epic}")
        else:
            logger.warning(f"⚠️ Keine gültige Antwort für Marktinfo {epic}")

        return {}

    def get_positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Gibt eine strukturierte Liste aller offenen Positionen zurück (mit Retry & Fehlerhandling).
        Rückgabeformat:
        {
            "positions": [
                {
                    "epic": str,
                    "dealId": str,
                    "direction": str,
                    "openLevel": float,
                    "profit": float,
                    "size": float,
                    "currency": str,
                    "market": Dict
                },
                ...
            ]
        }
        """
        if not self.cst or not self.security_token:
            logger.warning("⚠️ Nicht authentifiziert. get_positions() abgebrochen.")
            return {"positions": []}

        try:
            response = self.send_request("GET", "/api/v1/positions")
            if not response:
                logger.error("❌ get_positions() → Keine Antwort erhalten.")
                return {"positions": []}

            try:
                positions_data = response.json()
            except Exception as parse_err:
                logger.error(f"❌ Fehler beim Parsen der API-Antwort: {parse_err}")
                return {"positions": []}

            valid_positions = []

            for i, pos_data in enumerate(positions_data.get("positions", [])):
                try:
                    position = pos_data.get("position", {})
                    market = pos_data.get("market", {})

                    cleaned = {
                        "epic": market.get("epic", "UNKNOWN"),
                        "dealId": position.get("dealId", f"UNKNOWN_{i}"),
                        "direction": position.get("direction", "UNKNOWN"),
                        "openLevel": float(position.get("level", 0)),
                        "profit": float(position.get("upl", 0)),
                        "size": float(position.get("size", 0)),
                        "currency": position.get("currency", "CHF"),
                        "market": market
                    }

                    if cleaned["epic"] and cleaned["dealId"]:
                        valid_positions.append(cleaned)
                    else:
                        logger.warning(f"⚠️ Ungültige Position übersprungen: {cleaned}")

                except Exception as single_err:
                    logger.error(f"⚠️ Fehler bei Position {i}: {single_err}")
                    continue

            logger.info(f"✅ Offene Positionen gefunden: {len(valid_positions)}")
            return {"positions": valid_positions}

        except Exception as e:
            logger.exception("❌ Allgemeiner Fehler in get_positions()")
            return {"positions": []}

    def close_position(self, deal_id: str) -> Dict[str, Any]:
        """
        Schließt eine offene Position anhand der Deal-ID.
        Nutzt send_request() für stabilen & retryfähigen API-Zugriff.
        Gibt die API-Antwort zurück oder ein leeres Dict bei Fehlern.
        """
        if not self.cst or not self.security_token:
            logger.warning("⚠️ Nicht authentifiziert. close_position() abgebrochen.")
            return {}

        endpoint = f"/api/v1/positions/{deal_id}"
        response = self.send_request("DELETE", endpoint)

        if response is None:
            logger.error(f"❌ Keine Antwort beim Schließen der Position: {deal_id}")
            return {}

        try:
            response.raise_for_status()
            data = response.json()
            logger.info(f"📉 Position geschlossen: {deal_id}")
            return data

        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP-Fehler beim Schließen der Position {deal_id}: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Verbindungsfehler bei close_position(): {e}")
        except Exception as e:
            logger.exception(f"❌ Unerwarteter Fehler in close_position(): {e}")

        return {}

    def get_available_capital(self) -> float:
        """
        Gibt verfügbares Kapital in CHF zurück.
        Greift auf get_account_info() zu und filtert nach 'currency' == 'CHF'.
        """
        info = self.get_account_info()
        accounts = info.get("accounts", [])

        for acc in accounts:
            if acc.get("currency") == "CHF":
                capital = float(acc.get("balance", {}).get("available", 0.0))
                logger.info(f"💰 Verfügbares Kapital in CHF: {capital:.2f}")
                return capital

        logger.warning("⚠️ Kein CHF-Konto gefunden. Kapital = 0.0")
        return 0.0

    def berechne_trade_groesse(self, epic: str, debug: bool = False, longterm: bool = False) -> float:
        available_capital = self.get_available_capital()
        if available_capital <= 0:
            logger.warning("⚠️ Kein verfügbares Kapital – Tradegröße = 0")
            return 0.0
        """
        Berechnet die empfohlene Tradegröße für ein EPIC anhand:
        - verfügbarem Kapital (in CHF)
        - max. Kapital pro Trade (40 % von 80 % von 2/3)
        - aktuellem Preis und Mindestgröße (minDealSize)

        :param epic: Markt-EPIC (z. B. 'CS.D.BMW.DAILY.IP')
        :param debug: True → zusätzliche Debug-Ausgaben
        :return: float = berechnete Größe oder 0.0 bei Fehler
        """
        try:
            markt_info = self.get_market_info(epic)
            status = markt_info.get("instrument", {}).get("marketStatus", "UNKNOWN")
            if status != "TRADEABLE":
                logger.info(f"⛔ {epic} nicht handelbar (Status: {status})")
                return 0.0

            current_price = float(markt_info.get("snapshot", {}).get("bid", 0))
            min_unit = float(markt_info.get("instrument", {}).get("minDealSize", 1))

            if current_price <= 0:
                logger.warning(f"❌ Kein gültiger Preis für {epic}")
                return 0.0

            available_capital = self.get_available_capital()
            longterm_investment_aktiv = False  # <- zentral steuerbar
            verfuegbar = available_capital * (2 / 3) * (0.8 if longterm_investment_aktiv else 1.0)
            max_capital_per_trade = verfuegbar * 0.4

            raw_size = max_capital_per_trade / current_price
            size = (raw_size // min_unit) * min_unit
            size = round(size, 8)

            if size < min_unit:
                logger.info(f"⚠️ {epic} übersprungen: Größe {size} unter Mindestgröße {min_unit}")
                return 0.0

            if debug:
                logger.debug(
                    f"📐 {epic}: Preis={current_price:.4f} | Größe={size} | MinSize={min_unit} | Kapital={max_capital_per_trade:.2f}")

            return size

        except Exception as e:
            logger.exception(f"❌ Fehler bei berechne_trade_groesse({epic}): {e}")
            return 0.0

    def place_longterm_investment(self, asset: str, amount: float) -> bool:
        """
        Simuliert langfristige Investments – später durch echte API-Aufrufe ersetzen.
        """
        print(f"{Fore.GREEN}[LONGTERM] 📈 Investiere {amount:.2f} CHF in {asset}{Style.RESET_ALL}")
        return True  # Platzhalter – später mit Order-Logik erweitern

    def get_trending_markets(self) -> List[str]:
        """
        Gibt eine Liste trendender Märkte zurück.
        Hinweis: Du kannst andere Kategorien testen (z. B. "shares", "forex", "indices")
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/markets",
                params={"category": "cryptocurrencies"}  # Optional: Kategorie anpassen
            )
            data = response.json()
            return [m["epic"] for m in data.get("markets", []) if "epic" in m]
        except Exception as e:
            print(f"{Fore.RED}❌ Fehler beim Abrufen der Trending Markets: {e}{Style.RESET_ALL}")
            return []

    def get_all_markets(self) -> List[str]:
        """
        Liefert alle EPICs zurück, auf die du Zugriff hast.
        Nutzt send_request() für automatische Wiederholungen bei Rate-Limits.
        """
        if not self.cst or not self.security_token:
            logger.warning("⚠️ Nicht authentifiziert. get_all_markets() abgebrochen.")
            return []

        response = self.send_request("GET", "/api/v1/markets")

        if response is None:
            logger.error("❌ Keine Antwort bei get_all_markets() – API evtl. blockiert.")
            return []

        try:
            response.raise_for_status()
            data = response.json()
            epics = [m["epic"] for m in data.get("markets", []) if "epic" in m]
            logger.info(f"📦 Anzahl verfügbarer Märkte: {len(epics)}")
            return epics

        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP-Fehler bei get_all_markets(): {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Netzwerkfehler bei get_all_markets(): {e}")
        except Exception as e:
            logger.exception(f"❌ Unerwarteter Fehler in get_all_markets(): {e}")

        return []

    # ⬇️ HIER EINFÜGEN
    def pruefe_mindestgroesse(self, epic: str, size: float, min_unit: float) -> bool:
        """
        Gibt False zurück, wenn Größe < minDealSize, und gibt Warnung aus.
        """
        if size < min_unit:
            print(f"⚠️ {epic} übersprungen: {size} unter Mindestgröße ({min_unit})")
            return False
        return True