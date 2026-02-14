import json
import threading
import time
import urllib.request
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class FundingMonitor(QObject):
    alert_signal = pyqtSignal(object)
    log_signal = pyqtSignal(str)
    schedule_signal = pyqtSignal(int)

    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self._inflight = False
        self._alert_cache = set()
        self._max_cache = 20000

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.poll)
        self.schedule_signal.connect(self._schedule_next)

    def start(self):
        self._schedule_next(1000)

    def _schedule_next(self, ms):
        self.timer.start(max(1000, int(ms)))

    def poll(self):
        if self._inflight:
            self._schedule_next(60000)
            return
        self._inflight = True
        settings = self._snapshot_settings()
        thread = threading.Thread(
            target=self._poll_thread, args=(settings,), daemon=True
        )
        thread.start()

    def _snapshot_settings(self):
        exchanges = []
        if self.ui.funding_binance_check.isChecked():
            exchanges.append("binance")
        if self.ui.funding_bybit_check.isChecked():
            exchanges.append("bybit")

        minutes_text = self.ui.funding_minutes_edit.text().strip() or "15,5"
        threshold_pos_text = self.ui.funding_threshold_pos_edit.text().strip() or "1.0"
        threshold_neg_text = self.ui.funding_threshold_neg_edit.text().strip() or "1.0"

        return {
            "exchanges": exchanges,
            "minutes_text": minutes_text,
            "threshold_pos_text": threshold_pos_text,
            "threshold_neg_text": threshold_neg_text,
            "alert_before": self.ui.funding_before_check.isChecked(),
            "alert_percent": self.ui.funding_percent_check.isChecked(),
        }

    def _poll_thread(self, settings):
        try:
            data = []
            if "binance" in settings["exchanges"]:
                data.extend(self._fetch_binance())
            if "bybit" in settings["exchanges"]:
                data.extend(self._fetch_bybit())

            now_ms = int(time.time() * 1000)
            minutes_list = self._parse_minutes(settings["minutes_text"])
            threshold_pos = self._parse_threshold(settings["threshold_pos_text"])
            threshold_neg = self._parse_threshold(settings["threshold_neg_text"])

            min_minutes = None
            for item in data:
                next_time = item.get("next_funding_time")
                if not next_time:
                    continue
                minutes_to = max(0, int((next_time - now_ms) / 60000))
                signed_rate_pct = item["rate"] * 100
                passes_threshold = self._passes_threshold(
                    signed_rate_pct, threshold_pos, threshold_neg
                )
                if min_minutes is None or minutes_to < min_minutes:
                    min_minutes = minutes_to

                if settings["alert_before"] and minutes_list and passes_threshold:
                    for target_min in minutes_list:
                        if minutes_to == target_min:
                            key = self._cache_key(
                                "before",
                                item["exchange"],
                                item["symbol"],
                                next_time,
                                f"{target_min}:{threshold_pos}:{threshold_neg}",
                            )
                            if self._add_cache(key):
                                self.alert_signal.emit(
                                    {
                                        "exchange": item["exchange"],
                                        "symbol": item["symbol"],
                                        "signed_rate_pct": signed_rate_pct,
                                        "minutes_to": minutes_to,
                                        "next_funding_time": next_time,
                                        "kind": "before",
                                    }
                                )

                if settings["alert_percent"] and (
                    threshold_pos is not None or threshold_neg is not None
                ):
                    if self._passes_threshold(
                        signed_rate_pct, threshold_pos, threshold_neg
                    ):
                        key = self._cache_key(
                            "percent",
                            item["exchange"],
                            item["symbol"],
                            next_time,
                            f"{threshold_pos}:{threshold_neg}",
                        )
                        if self._add_cache(key):
                            self.alert_signal.emit(
                                {
                                    "exchange": item["exchange"],
                                    "symbol": item["symbol"],
                                    "signed_rate_pct": signed_rate_pct,
                                    "minutes_to": minutes_to,
                                    "next_funding_time": next_time,
                                    "kind": "percent",
                                }
                            )

            interval_ms = 300000
            if min_minutes is not None and min_minutes <= 60:
                interval_ms = 60000
            self.schedule_signal.emit(interval_ms)
        except Exception as exc:
            self.log_signal.emit(f"Funding error: {exc}")
            self.schedule_signal.emit(60000)
        finally:
            self._inflight = False

    def _cache_key(self, kind, exchange, symbol, next_time, extra):
        return f"{kind}:{exchange}:{symbol}:{next_time}:{extra}"

    def _add_cache(self, key):
        if key in self._alert_cache:
            return False
        self._alert_cache.add(key)
        if len(self._alert_cache) > self._max_cache:
            self._alert_cache = set(list(self._alert_cache)[-self._max_cache :])
        return True

    def _parse_minutes(self, text):
        minutes = []
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                val = int(float(part))
                if val >= 0:
                    minutes.append(val)
            except Exception:
                continue
        return sorted(set(minutes))

    def _parse_threshold(self, text):
        try:
            val = float(text)
            if val <= 0:
                return None
            return val
        except Exception:
            return None

    def _passes_threshold(self, signed_rate_pct, threshold_pos, threshold_neg):
        if threshold_pos is None and threshold_neg is None:
            return True
        if threshold_pos is not None and signed_rate_pct >= threshold_pos:
            return True
        if threshold_neg is not None and signed_rate_pct <= -threshold_neg:
            return True
        return False

    def _fetch_json(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "TF-Alerter"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _fetch_binance(self):
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        data = self._fetch_json(url)
        items = []
        if not isinstance(data, list):
            return items
        for entry in data:
            try:
                symbol = entry.get("symbol")
                rate = float(entry.get("lastFundingRate", 0))
                next_time = int(entry.get("nextFundingTime", 0))
            except Exception:
                continue
            if not symbol or not next_time:
                continue
            items.append(
                {
                    "exchange": "Binance",
                    "symbol": symbol,
                    "rate": rate,
                    "next_funding_time": next_time,
                }
            )
        return items

    def _fetch_bybit(self):
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        payload = self._fetch_json(url)
        result = payload.get("result", {}) if isinstance(payload, dict) else {}
        listing = result.get("list", [])
        items = []
        if not isinstance(listing, list):
            return items
        for entry in listing:
            try:
                symbol = entry.get("symbol")
                rate = float(entry.get("fundingRate", 0))
                next_time = int(entry.get("nextFundingTime", 0))
            except Exception:
                continue
            if not symbol or not next_time:
                continue
            items.append(
                {
                    "exchange": "Bybit",
                    "symbol": symbol,
                    "rate": rate,
                    "next_funding_time": next_time,
                }
            )
        return items
