
# capital_api.py

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

        print(f"🧠 Session gültig? → {self.session_manager.is_session_valid()} (Letzter Start: {self.session_manager.last_session_time})")
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

        response = self.send_http_request("POST", endpoint, data=order_payload)

        if response and response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.error("❌ JSON-Fehler bei Order-Antwort.")
                return None
        else:
            logger.error(
                f"❌ Order fehlgeschlagen – Status: {response.status_code if response else 'keine Antwort'}")
            return None

    def send_request(self, method: str, endpoint: str, data=None, params=None) -> Optional[requests.Response]:
        return self.send_http_request(method, endpoint, data=data, params=params)

    def send_http_request(self, method: str, endpoint: str, data=None, params=None, headers=None, timeout=5) -> Optional[requests.Response]:
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
