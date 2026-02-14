import json
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class FundingMonitor(QObject):
    alert_signal = pyqtSignal(object)
    log_signal = pyqtSignal(object)
    status_signal = pyqtSignal(object)
    schedule_signal = pyqtSignal(int)

    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self._inflight = False
        self._alert_cache = set()
        self._max_cache = 20000
        self._last_exchange_signature = ()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.poll)
        self.schedule_signal.connect(self._schedule_next)

    def start(self):
        self._schedule_next(1000)

    def stop(self):
        """Останавливает мониторинг фандинга"""
        self.timer.stop()

    def clear_cache(self):
        """Сбрасывает кэш, чтобы повторно логировать текущие записи."""
        self._alert_cache.clear()

    def _schedule_next(self, ms):
        self.timer.start(max(1000, int(ms)))

    def poll(self):
        if self._inflight:
            self._schedule_next(60000)
            return
        settings = self._snapshot_settings()
        signature = tuple(sorted(settings.get("exchanges", [])))
        if signature != self._last_exchange_signature:
            self.clear_cache()
            self._last_exchange_signature = signature

        self._inflight = True
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
        if (
            getattr(self.ui, "funding_okx_check", None)
            and self.ui.funding_okx_check.isChecked()
        ):
            exchanges.append("okx")
        if (
            getattr(self.ui, "funding_gate_check", None)
            and self.ui.funding_gate_check.isChecked()
        ):
            exchanges.append("gate")
        if (
            getattr(self.ui, "funding_bitget_check", None)
            and self.ui.funding_bitget_check.isChecked()
        ):
            exchanges.append("bitget")

        minutes_text = self.ui.funding_minutes_edit.text().strip() or "15,5"
        threshold_pos_text = self.ui.funding_threshold_pos_edit.text().strip() or "0"
        threshold_neg_text = self.ui.funding_threshold_neg_edit.text().strip() or "0"

        return {
            "exchanges": exchanges,
            "minutes_text": minutes_text,
            "threshold_pos_text": threshold_pos_text,
            "threshold_neg_text": threshold_neg_text,
        }

    def _poll_thread(self, settings):
        exchange_defs = [
            ("binance", "Binance", self._fetch_binance),
            ("bybit", "Bybit", self._fetch_bybit),
            ("okx", "OKX", self._fetch_okx),
            ("gate", "Gate", self._fetch_gate),
            ("bitget", "Bitget", self._fetch_bitget),
        ]
        selected = set(settings.get("exchanges", []))
        status_map = {
            key: {
                "name": name,
                "enabled": key in selected,
                "fetched": 0,
                "passed": 0,
                "error": "",
            }
            for key, name, _ in exchange_defs
        }

        try:
            data = []
            interval_ms = 60000
            for key, name, fetcher in exchange_defs:
                if key not in selected:
                    continue
                items, error_text = self._safe_fetch_exchange_with_status(fetcher, name)
                status_map[key]["fetched"] = len(items)
                status_map[key]["error"] = error_text
                data.extend(items)

            now_ms = int(time.time() * 1000)
            minutes_list = self._parse_minutes(settings["minutes_text"])
            threshold_pos = self._parse_threshold(settings["threshold_pos_text"])
            threshold_neg = self._parse_threshold(settings["threshold_neg_text"])

            min_minutes = None
            # Находим максимальное значение из minutes_list для фильтрации логов
            max_minutes_filter = max(minutes_list) if minutes_list else 999999
            exchange_to_key = {
                "binance": "binance",
                "bybit": "bybit",
                "okx": "okx",
                "gate": "gate",
                "bitget": "bitget",
            }

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

                # Логируем все, что проходит порог и в пределах максимального времени
                if passes_threshold and minutes_to <= max_minutes_filter:
                    exchange_key = exchange_to_key.get(
                        str(item.get("exchange", "")).strip().lower(), ""
                    )
                    if exchange_key in status_map:
                        status_map[exchange_key]["passed"] += 1

                    log_key = self._cache_key(
                        "log",
                        item["exchange"],
                        item["symbol"],
                        next_time,
                        f"{threshold_pos}:{threshold_neg}",
                    )
                    if self._add_cache(log_key):
                        self.log_signal.emit(
                            {
                                "exchange": item["exchange"],
                                "symbol": item["symbol"],
                                "signed_rate_pct": signed_rate_pct,
                                "minutes_to": minutes_to,
                                "next_funding_time": next_time,
                                "kind": "log",
                            }
                        )

                    # Алерт только при точном совпадении минут
                    if minutes_list:
                        for target_min in minutes_list:
                            if minutes_to == target_min:
                                alert_key = self._cache_key(
                                    "alert",
                                    item["exchange"],
                                    item["symbol"],
                                    next_time,
                                    f"{target_min}:{threshold_pos}:{threshold_neg}",
                                )
                                if self._add_cache(alert_key):
                                    self.alert_signal.emit(
                                        {
                                            "exchange": item["exchange"],
                                            "symbol": item["symbol"],
                                            "signed_rate_pct": signed_rate_pct,
                                            "minutes_to": minutes_to,
                                            "next_funding_time": next_time,
                                            "kind": "alert",
                                        }
                                    )
            self.status_signal.emit(
                {
                    "updated_at_ms": now_ms,
                    "exchanges": status_map,
                }
            )
            self.schedule_signal.emit(interval_ms)
        except Exception as exc:
            self.log_signal.emit(f"Funding error: {exc}")
            self.status_signal.emit(
                {
                    "updated_at_ms": int(time.time() * 1000),
                    "exchanges": status_map,
                    "error": str(exc),
                }
            )
            self.schedule_signal.emit(60000)
        finally:
            self._inflight = False

    def _safe_fetch_exchange(self, fetcher, exchange_name):
        try:
            items = fetcher()
            return items if isinstance(items, list) else []
        except Exception as exc:
            self.log_signal.emit(f"Funding fetch error ({exchange_name}): {exc}")
            return []

    def _safe_fetch_exchange_with_status(self, fetcher, exchange_name):
        try:
            items = fetcher()
            if not isinstance(items, list):
                return [], ""
            return items, ""
        except Exception as exc:
            text = str(exc)
            self.log_signal.emit(f"Funding fetch error ({exchange_name}): {text}")
            return [], text

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

    def _fetch_okx(self):
        tickers_url = "https://www.okx.com/api/v5/market/tickers?instType=SWAP"
        payload = self._fetch_json(tickers_url)
        listing = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(listing, list):
            return []

        inst_ids = []
        for entry in listing:
            try:
                inst_id = str(entry.get("instId", ""))
            except Exception:
                continue
            if not inst_id.endswith("-SWAP"):
                continue
            if "-USDT-" not in inst_id:
                continue
            inst_ids.append(inst_id)

        items = []
        if not inst_ids:
            return items

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(
                    self._fetch_json,
                    f"https://www.okx.com/api/v5/public/funding-rate?instId={inst_id}",
                ): inst_id
                for inst_id in inst_ids
            }
            for future in as_completed(futures):
                inst_id = futures[future]
                try:
                    result = future.result()
                    rows = result.get("data", []) if isinstance(result, dict) else []
                    if not rows:
                        continue
                    row = rows[0]
                    rate = float(row.get("fundingRate", 0) or 0)
                    next_time = int(float(row.get("nextFundingTime", 0) or 0))
                except Exception:
                    continue
                if not next_time:
                    continue
                symbol = inst_id.replace("-SWAP", "").replace("-", "")
                items.append(
                    {
                        "exchange": "OKX",
                        "symbol": symbol,
                        "rate": rate,
                        "next_funding_time": next_time,
                    }
                )
        return items

    def _fetch_gate(self):
        url = "https://api.gateio.ws/api/v4/futures/usdt/contracts"
        listing = self._fetch_json(url)
        items = []
        if not isinstance(listing, list):
            return items
        for entry in listing:
            try:
                contract = str(entry.get("name", ""))
                rate = float(entry.get("funding_rate", 0) or 0)
                next_time_raw = entry.get("funding_next_apply")
                if next_time_raw is None:
                    next_time_raw = entry.get("next_funding_time", 0)
                next_time = int(float(next_time_raw or 0))
            except Exception:
                continue
            if not contract or not next_time:
                continue
            if next_time < 10**12:
                next_time *= 1000
            symbol = contract.replace("_", "")
            items.append(
                {
                    "exchange": "Gate",
                    "symbol": symbol,
                    "rate": rate,
                    "next_funding_time": next_time,
                }
            )
        return items

    def _fetch_bitget(self):
        url = "https://api.bitget.com/api/v2/mix/market/current-fund-rate?productType=USDT-FUTURES"
        payload = self._fetch_json(url)
        listing = payload.get("data", []) if isinstance(payload, dict) else []
        items = []
        if not isinstance(listing, list):
            return items
        for entry in listing:
            try:
                symbol = str(entry.get("symbol", ""))
                rate = float(entry.get("fundingRate", 0) or 0)
                next_time = int(float(entry.get("nextUpdate", 0) or 0))
            except Exception:
                continue
            if not symbol or not next_time:
                continue
            if next_time < 10**12:
                next_time *= 1000
            items.append(
                {
                    "exchange": "Bitget",
                    "symbol": symbol,
                    "rate": rate,
                    "next_funding_time": next_time,
                }
            )
        return items
