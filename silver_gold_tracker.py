#!/usr/bin/env python3
"""Silver/Gold ratio tracker widget (terminal-based).

Default normalized symbols:
- Gold: XAUUSD
- Silver: XAGUSD

Usage:
    python silver_gold_tracker.py --interval 30
    python silver_gold_tracker.py --once
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import statistics
import sys
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Protocol

import requests

YAHOO_CHART_ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
STOOQ_QUOTE_ENDPOINT = "https://stooq.com/q/l/"
STOOQ_HISTORY_ENDPOINT = "https://stooq.com/q/d/l/"

DEFAULT_SYMBOL_ALIASES = {
    "GC=F": "XAUUSD",
    "SI=F": "XAGUSD",
    "XAU/USD": "XAUUSD",
    "XAG/USD": "XAGUSD",
    "XAUUSD": "XAUUSD",
    "XAGUSD": "XAGUSD",
}


@dataclass(frozen=True)
class PriceSnapshot:
    symbol: str
    price: float
    source_timestamp: dt.datetime
    market_status: str = "unknown"
    bid: float | None = None
    ask: float | None = None
    is_last_trade: bool | None = None
    provider: str | None = None

    @property
    def timestamp(self) -> dt.datetime:
        """Backward-compatible alias used by existing renderer code."""
        return self.source_timestamp


@dataclass(frozen=True)
class RatioSnapshot:
    gold: PriceSnapshot
    silver: PriceSnapshot
    ratio: float

    @property
    def timestamp(self) -> dt.datetime:
        return max(self.gold.timestamp, self.silver.timestamp)


@dataclass(frozen=True)
class QualityStatus:
    state: str
    provider_used: str
    detail: str = ""

    @property
    def activity_label(self) -> str:
        if self.state == "synced":
            return "Synced"
        if self.state == "fallback_used":
            return "Fallback used"
        if self.state == "stale_pair":
            return "Stale pair"
        return "Quality unknown"


class YahooFinanceProvider:
    """Pulls latest market prices from Yahoo Finance chart API."""

    symbol_map = {
        "XAUUSD": "GC=F",
        "XAGUSD": "SI=F",
    }

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = 3
        self.retry_backoff_seconds = 1.5
        self.min_request_spacing_seconds = 8.0
        self._cache: dict[str, PriceSnapshot] = {}
        self._last_request_monotonic: dict[str, float] = {}
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0 Safari/537.36"
                )
            }
        )

    def get_latest_prices(self, symbols: list[str]) -> dict[str, PriceSnapshot]:
        out: dict[str, PriceSnapshot] = {}
        for symbol in symbols:
            out[symbol] = self.get_latest_price(symbol)
            time.sleep(0.25)
        return out

    def get_latest_price(self, symbol: str) -> PriceSnapshot:
        provider_symbol = self.symbol_map.get(normalize_symbol(symbol), symbol)
        now = time.monotonic()
        last_request = self._last_request_monotonic.get(provider_symbol)
        if (
            provider_symbol in self._cache
            and last_request is not None
            and now - last_request < self.min_request_spacing_seconds
        ):
            return self._cache[provider_symbol]

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self._last_request_monotonic[provider_symbol] = time.monotonic()
                response = self.session.get(
                    YAHOO_CHART_ENDPOINT.format(symbol=provider_symbol),
                    params={"interval": "1m", "range": "1d"},
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()

                result = payload.get("chart", {}).get("result")
                if not result:
                    raise ValueError(f"No chart result for symbol {provider_symbol!r}")

                data = result[0]
                meta = data.get("meta", {})
                timestamp_raw = meta.get("regularMarketTime")
                market_price = meta.get("regularMarketPrice")

                if timestamp_raw is None or market_price is None:
                    raise ValueError(f"Missing market fields for symbol {provider_symbol!r}")

                snapshot = PriceSnapshot(
                    symbol=normalize_symbol(symbol),
                    price=float(market_price),
                    source_timestamp=dt.datetime.fromtimestamp(timestamp_raw, tz=dt.timezone.utc),
                    market_status=str(meta.get("marketState", "unknown")).lower(),
                    provider="yahoo",
                )
                self._cache[provider_symbol] = snapshot
                return snapshot
            except requests.HTTPError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else None
                if status == 429 and attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                if status == 429 and provider_symbol in self._cache:
                    return self._cache[provider_symbol]
                raise
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                if provider_symbol in self._cache:
                    return self._cache[provider_symbol]
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Unexpected provider error for symbol {provider_symbol}")


class StooqProvider:
    """Fallback provider using Stooq CSV endpoint."""

    symbol_map = {
        "GC=F": "xauusd",
        "SI=F": "xagusd",
        "XAUUSD": "xauusd",
        "XAGUSD": "xagusd",
    }

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0 Safari/537.36"
                )
            }
        )

    def _map_symbol(self, symbol: str) -> str:
        normalized = normalize_symbol(symbol)
        return self.symbol_map.get(normalized, normalized.lower())

    def get_latest_price(self, symbol: str) -> PriceSnapshot:
        stooq_symbol = self._map_symbol(symbol)
        response = self.session.get(
            STOOQ_QUOTE_ENDPOINT,
            params={"s": stooq_symbol, "i": "d"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        text = response.text.strip()
        if not text:
            raise ValueError(f"No response body for symbol {symbol!r}")

        parts = text.split(",")
        if len(parts) < 7:
            raise ValueError(f"Unexpected CSV format for symbol {symbol!r}: {text!r}")

        date_raw = parts[1]
        time_raw = parts[2]
        close_raw = parts[6]
        if close_raw in {"", "N/D"}:
            raise ValueError(f"Missing close price for symbol {symbol!r}")

        ts = dt.datetime.strptime(f"{date_raw} {time_raw}", "%Y%m%d %H%M%S").replace(tzinfo=dt.timezone.utc)
        return PriceSnapshot(
            symbol=normalize_symbol(symbol),
            price=float(close_raw),
            source_timestamp=ts,
            market_status="unknown",
            provider="stooq",
        )

    def get_latest_prices(self, symbols: list[str]) -> dict[str, PriceSnapshot]:
        out: dict[str, PriceSnapshot] = {}
        for symbol in symbols:
            out[symbol] = self.get_latest_price(symbol)
            time.sleep(0.15)
        return out


class GoogleProvider(StooqProvider):
    """Google source option (currently backed by stable quote feed mapping)."""


def normalize_symbol(symbol: str) -> str:
    compact = symbol.strip().upper().replace("-", "").replace("_", "")
    compact = compact.replace(" ", "")
    if "/" in symbol:
        compact = symbol.strip().upper().replace("/", "")
    return DEFAULT_SYMBOL_ALIASES.get(symbol.strip().upper(), DEFAULT_SYMBOL_ALIASES.get(compact, compact))


def _parse_timestamp_utc(value: Any) -> dt.datetime:
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(float(value), tz=dt.timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return dt.datetime.now(tz=dt.timezone.utc)
        try:
            return dt.datetime.fromtimestamp(float(text), tz=dt.timezone.utc)
        except ValueError:
            pass
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = dt.datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc)
        except ValueError:
            return dt.datetime.now(tz=dt.timezone.utc)
    return dt.datetime.now(tz=dt.timezone.utc)


class TwelveDataProvider:
    """Free-ish spot feed via Twelve Data quote endpoint (XAU/USD, XAG/USD)."""

    symbol_map = {
        "XAUUSD": "XAU/USD",
        "XAGUSD": "XAG/USD",
    }

    def __init__(
        self,
        api_base_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.api_base_url = (api_base_url or os.getenv("TWELVE_DATA_BASE_URL") or "https://api.twelvedata.com").rstrip(
            "/"
        )
        self.api_token = api_token or os.getenv("TWELVE_DATA_API_TOKEN")
        self.session = requests.Session()

    def _map_symbol(self, symbol: str) -> str:
        return self.symbol_map.get(normalize_symbol(symbol), symbol)

    def get_latest_price(self, symbol: str) -> PriceSnapshot:
        if not self.api_token:
            raise ValueError("Missing TWELVE_DATA_API_TOKEN for Twelve Data provider")

        response = self.session.get(
            f"{self.api_base_url}/quote",
            params={"symbol": self._map_symbol(symbol), "apikey": self.api_token},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") == "error":
            raise ValueError(f"Twelve Data error: {payload.get('message', 'unknown error')}")

        price_raw = payload.get("close") or payload.get("price")
        if price_raw is None:
            raise ValueError(f"Twelve Data missing price for symbol {symbol!r}")

        market_status = "open" if str(payload.get("is_market_open", "")).lower() == "true" else "closed"
        if payload.get("is_market_open") is None:
            market_status = "unknown"

        return PriceSnapshot(
            symbol=normalize_symbol(symbol),
            price=float(price_raw),
            source_timestamp=_parse_timestamp_utc(payload.get("timestamp") or payload.get("datetime")),
            market_status=market_status,
            bid=float(payload["bid"]) if payload.get("bid") not in {None, ""} else None,
            ask=float(payload["ask"]) if payload.get("ask") not in {None, ""} else None,
            is_last_trade=True,
            provider="twelve",
        )

    def get_latest_prices(self, symbols: list[str]) -> dict[str, PriceSnapshot]:
        out: dict[str, PriceSnapshot] = {}
        for symbol in symbols:
            out[symbol] = self.get_latest_price(symbol)
            time.sleep(0.2)
        return out


class MetalsAPIProvider:
    """Premium-ish LBMA-aligned spot feed using Metals-API latest endpoint."""

    symbol_map = {
        "XAUUSD": "XAU",
        "XAGUSD": "XAG",
    }

    def __init__(
        self,
        api_base_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.api_base_url = (api_base_url or os.getenv("METALS_API_BASE_URL") or "https://metals-api.com/api").rstrip(
            "/"
        )
        self.api_token = api_token or os.getenv("METALS_API_TOKEN")
        self.session = requests.Session()

    def get_latest_prices(self, symbols: list[str]) -> dict[str, PriceSnapshot]:
        if not self.api_token:
            raise ValueError("Missing METALS_API_TOKEN for Metals-API provider")

        normalized = [normalize_symbol(s) for s in symbols]
        feed_symbols = [self.symbol_map[s] for s in normalized if s in self.symbol_map]
        if not feed_symbols:
            raise ValueError("Metals-API provider received unsupported symbols")

        response = self.session.get(
            f"{self.api_base_url}/latest",
            params={
                "access_key": self.api_token,
                "base": "USD",
                "symbols": ",".join(feed_symbols),
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("success") is False:
            raise ValueError(f"Metals-API error: {payload.get('error')}")

        rates = payload.get("rates", {})
        ts = _parse_timestamp_utc(payload.get("timestamp"))
        out: dict[str, PriceSnapshot] = {}
        for raw_symbol, normalized_symbol in zip(symbols, normalized):
            metal = self.symbol_map.get(normalized_symbol)
            if metal is None or metal not in rates:
                raise ValueError(f"Metals-API missing rate for symbol {raw_symbol!r}")
            metal_per_usd = float(rates[metal])
            if metal_per_usd <= 0:
                raise ValueError(f"Metals-API invalid rate for symbol {raw_symbol!r}")
            usd_per_metal = 1.0 / metal_per_usd
            out[raw_symbol] = PriceSnapshot(
                symbol=normalized_symbol,
                price=usd_per_metal,
                source_timestamp=ts,
                market_status="unknown",
                is_last_trade=False,
                provider="metalsapi",
            )
        return out


class PolygonProvider:
    """Premium provider using Polygon FX snapshots as proxy pricing feed."""

    symbol_map = {
        "XAUUSD": "C:XAUUSD",
        "XAGUSD": "C:XAGUSD",
    }

    def __init__(
        self,
        api_base_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.api_base_url = (api_base_url or os.getenv("POLYGON_BASE_URL") or "https://api.polygon.io").rstrip("/")
        self.api_token = api_token or os.getenv("POLYGON_API_TOKEN")
        self.session = requests.Session()

    def get_latest_price(self, symbol: str) -> PriceSnapshot:
        if not self.api_token:
            raise ValueError("Missing POLYGON_API_TOKEN for Polygon provider")
        normalized = normalize_symbol(symbol)
        ticker = self.symbol_map.get(normalized)
        if ticker is None:
            raise ValueError(f"Polygon provider does not support symbol {symbol!r}")
        response = self.session.get(
            f"{self.api_base_url}/v3/snapshot",
            params={"ticker.any_of": ticker, "apiKey": self.api_token},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        if not results:
            raise ValueError(f"Polygon returned no snapshot rows for symbol {symbol!r}")
        row = results[0]
        session = row.get("session", {}) if isinstance(row.get("session"), dict) else {}
        last_quote = row.get("last_quote", {}) if isinstance(row.get("last_quote"), dict) else {}
        updated_raw = session.get("last_updated") or last_quote.get("last_updated")
        return PriceSnapshot(
            symbol=normalized,
            price=float(session.get("close") or session.get("price") or row.get("value")),
            source_timestamp=_parse_timestamp_utc(updated_raw / 1_000_000_000 if isinstance(updated_raw, int) else updated_raw),
            market_status="open" if session else "unknown",
            bid=float(last_quote["bid"]) if last_quote.get("bid") is not None else None,
            ask=float(last_quote["ask"]) if last_quote.get("ask") is not None else None,
            is_last_trade=True,
            provider="polygon",
        )

    def get_latest_prices(self, symbols: list[str]) -> dict[str, PriceSnapshot]:
        out: dict[str, PriceSnapshot] = {}
        for symbol in symbols:
            out[symbol] = self.get_latest_price(symbol)
            time.sleep(0.15)
        return out


class MarketDataProvider(Protocol):
    def get_latest_prices(self, symbols: list[str]) -> dict[str, PriceSnapshot]:
        ...


class FallbackProvider:
    """Primary provider with fallback provider on failure."""

    def __init__(self, primary: MarketDataProvider, fallback: MarketDataProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    def get_latest_prices(self, symbols: list[str]) -> dict[str, PriceSnapshot]:
        try:
            return self.primary.get_latest_prices(symbols)
        except Exception:
            return self.fallback.get_latest_prices(symbols)


def create_provider(name: str, provider_config: dict[str, dict[str, str]] | None = None) -> MarketDataProvider:
    key = name.strip().lower()
    provider_config = provider_config or {}
    if key == "yahoo":
        return YahooFinanceProvider()
    if key == "stooq":
        return StooqProvider()
    if key == "google":
        return GoogleProvider()
    if key == "twelve":
        cfg = provider_config.get("twelve", {})
        return TwelveDataProvider(
            api_token=cfg.get("api_token") or None,
            api_base_url=cfg.get("api_base_url") or None,
        )
    if key == "metalsapi":
        cfg = provider_config.get("metalsapi", {})
        return MetalsAPIProvider(
            api_token=cfg.get("api_token") or None,
            api_base_url=cfg.get("api_base_url") or None,
        )
    if key == "polygon":
        cfg = provider_config.get("polygon", {})
        return PolygonProvider(
            api_token=cfg.get("api_token") or None,
            api_base_url=cfg.get("api_base_url") or None,
        )
    raise ValueError(f"Unknown provider {name!r}")


def create_provider_chain(
    primary_name: str,
    fallback_name: str = "none",
    provider_config: dict[str, dict[str, str]] | None = None,
) -> MarketDataProvider:
    primary = create_provider(primary_name, provider_config=provider_config)
    if fallback_name != "none" and fallback_name != primary_name:
        return FallbackProvider(primary, create_provider(fallback_name, provider_config=provider_config))
    if primary_name in {"twelve", "metalsapi", "polygon"}:
        return FallbackProvider(primary, StooqProvider())
    return primary


def _history_cutoff(period: str) -> dt.datetime | None:
    now = dt.datetime.now(tz=dt.timezone.utc)
    period = period.upper()
    days_map = {
        "1M": 30,
        "3M": 90,
        "6M": 180,
        "1Y": 365,
        "2Y": 730,
        "5Y": 1825,
        "10Y": 3650,
        "MAX": None,
    }
    days = days_map.get(period, 365)
    if days is None:
        return None
    return now - dt.timedelta(days=days)


def _load_stooq_history(symbol: str, period: str) -> list[tuple[dt.datetime, float]]:
    mapped = StooqProvider.symbol_map.get(normalize_symbol(symbol), symbol.lower())
    response = requests.get(
        STOOQ_HISTORY_ENDPOINT,
        params={"s": mapped, "i": "d"},
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    lines = response.text.strip().splitlines()
    if len(lines) <= 1:
        return []

    cutoff = _history_cutoff(period)
    out: list[tuple[dt.datetime, float]] = []
    for row in lines[1:]:
        parts = row.split(",")
        if len(parts) < 5:
            continue
        date_raw = parts[0]
        close_raw = parts[4]
        if close_raw in {"", "N/D"}:
            continue
        ts = dt.datetime.strptime(date_raw, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
        if cutoff is not None and ts < cutoff:
            continue
        out.append((ts, float(close_raw)))
    return out


def _load_yahoo_history(symbol: str, period: str) -> list[tuple[dt.datetime, float]]:
    mapped = YahooFinanceProvider.symbol_map.get(normalize_symbol(symbol), symbol)
    period_map = {
        "1M": "1mo",
        "3M": "3mo",
        "6M": "6mo",
        "1Y": "1y",
        "2Y": "2y",
        "5Y": "5y",
        "10Y": "10y",
        "MAX": "max",
    }
    response = requests.get(
        YAHOO_CHART_ENDPOINT.format(symbol=mapped),
        params={"interval": "1d", "range": period_map.get(period.upper(), "1y")},
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("chart", {}).get("result")
    if not result:
        return []
    data = result[0]
    timestamps = data.get("timestamp", []) or []
    closes = (
        data.get("indicators", {})
        .get("quote", [{}])[0]
        .get("close", [])
        or []
    )
    out: list[tuple[dt.datetime, float]] = []
    for ts_raw, close in zip(timestamps, closes):
        if close is None:
            continue
        ts = dt.datetime.fromtimestamp(ts_raw, tz=dt.timezone.utc)
        out.append((ts, float(close)))
    return out


def load_ratio_history(
    provider_name: str,
    gold_symbol: str = "XAUUSD",
    silver_symbol: str = "XAGUSD",
    period: str = "1Y",
) -> list[tuple[dt.datetime, float]]:
    key = provider_name.lower()
    if key == "yahoo":
        gold = _load_yahoo_history(gold_symbol, period)
        silver = _load_yahoo_history(silver_symbol, period)
    else:
        gold = _load_stooq_history(gold_symbol, period)
        silver = _load_stooq_history(silver_symbol, period)

    silver_map = {t: v for t, v in silver}
    out: list[tuple[dt.datetime, float]] = []
    for t, g in gold:
        s = silver_map.get(t)
        if s is None or s <= 0:
            continue
        out.append((t, g / s))
    return out


def load_price_history(
    provider_name: str,
    symbol: str,
    period: str = "1Y",
) -> list[tuple[dt.datetime, float]]:
    key = provider_name.lower()
    if key == "yahoo":
        return _load_yahoo_history(symbol, period)
    return _load_stooq_history(symbol, period)


class RatioTracker:
    """Tracks ratio snapshots and renders a terminal widget."""

    def __init__(
        self,
        provider: MarketDataProvider,
        gold_symbol: str = "XAUUSD",
        silver_symbol: str = "XAGUSD",
        max_points: int = 120,
        retry_delay_seconds: float = 0.35,
        skip_quality_checks: bool = False,
    ) -> None:
        self.provider = provider
        self.gold_symbol = gold_symbol
        self.silver_symbol = silver_symbol
        self.history: Deque[RatioSnapshot] = deque(maxlen=max_points)
        self.retry_delay_seconds = retry_delay_seconds
        self.skip_quality_checks = skip_quality_checks
        self.last_quality_status = QualityStatus(state="unknown", provider_used="n/a", detail="No samples yet")

        # Per-provider quality windows; tuned for live snapshots.
        # quote_age_seconds = max age of each leg relative to now (UTC).
        # pair_delta_seconds = max timestamp spread between gold/silver legs.
        self.quality_thresholds: dict[str, dict[str, float]] = {
            "yahoo": {"quote_age_seconds": 35.0, "pair_delta_seconds": 5.0},
            "stooq": {"quote_age_seconds": 120.0, "pair_delta_seconds": 10.0},
            "google": {"quote_age_seconds": 120.0, "pair_delta_seconds": 10.0},
            "default": {"quote_age_seconds": 60.0, "pair_delta_seconds": 5.0},
        }

    def _provider_name(self, provider: MarketDataProvider) -> str:
        if isinstance(provider, YahooFinanceProvider):
            return "yahoo"
        if isinstance(provider, StooqProvider):
            return "stooq"
        if isinstance(provider, GoogleProvider):
            return "google"
        return provider.__class__.__name__.lower()

    def _provider_candidates(self) -> list[tuple[str, MarketDataProvider]]:
        if isinstance(self.provider, FallbackProvider):
            return [
                (self._provider_name(self.provider.primary), self.provider.primary),
                (self._provider_name(self.provider.fallback), self.provider.fallback),
            ]
        return [(self._provider_name(self.provider), self.provider)]

    def _evaluate_quality(
        self,
        provider_name: str,
        gold: PriceSnapshot,
        silver: PriceSnapshot,
    ) -> tuple[bool, str]:
        threshold = self.quality_thresholds.get(provider_name, self.quality_thresholds["default"])
        now = dt.datetime.now(tz=dt.timezone.utc)
        pair_delta = abs((gold.timestamp - silver.timestamp).total_seconds())
        gold_age = (now - gold.timestamp).total_seconds()
        silver_age = (now - silver.timestamp).total_seconds()
        max_age = max(gold_age, silver_age)

        if pair_delta > threshold["pair_delta_seconds"]:
            return False, (
                f"timestamp spread {pair_delta:.1f}s exceeds "
                f"{threshold['pair_delta_seconds']:.1f}s for {provider_name}"
            )
        if max_age > threshold["quote_age_seconds"]:
            return False, (
                f"quote age {max_age:.1f}s exceeds "
                f"{threshold['quote_age_seconds']:.1f}s for {provider_name}"
            )
        return True, ""

    def refresh(self) -> RatioSnapshot:
        candidates = self._provider_candidates()
        stale_failures: list[str] = []
        used_fallback = False

        for idx, (provider_name, provider) in enumerate(candidates):
            for attempt in range(2):  # initial + one retry
                prices = provider.get_latest_prices([self.gold_symbol, self.silver_symbol])
                gold = prices[self.gold_symbol]
                silver = prices[self.silver_symbol]
                is_ok, reason = self._evaluate_quality(provider_name, gold, silver)
                if self.skip_quality_checks:
                    is_ok = True
                    reason = "Quality checks skipped by user"
                if is_ok:
                    if gold.price <= 0:
                        raise ValueError("Gold price must be positive")
                    if silver.price <= 0:
                        raise ValueError("Silver price must be positive")
                    ratio = gold.price / silver.price
                    snapshot = RatioSnapshot(gold=gold, silver=silver, ratio=ratio)
                    self.history.append(snapshot)
                    state = "fallback_used" if used_fallback or idx > 0 else "synced"
                    self.last_quality_status = QualityStatus(
                        state=state,
                        provider_used=provider_name,
                        detail=(
                            "Quality checks skipped by user"
                            if self.skip_quality_checks
                            else "Recovered using fallback provider"
                            if state == "fallback_used"
                            else "Gold/Silver leg timestamps are within limits"
                        ),
                    )
                    return snapshot
                stale_failures.append(reason)
                self.last_quality_status = QualityStatus(
                    state="stale_pair",
                    provider_used=provider_name,
                    detail=reason,
                )
                if attempt == 0:
                    time.sleep(self.retry_delay_seconds)
                    continue
                break

            used_fallback = True

        if stale_failures:
            raise ValueError(f"All provider quotes failed quality checks: {'; '.join(stale_failures)}")
        raise ValueError("No quote providers available")

    def render(self) -> str:
        if not self.history:
            return "No data yet."

        latest = self.history[-1]
        ratios = [s.ratio for s in self.history]
        mean_ratio = statistics.fmean(ratios)
        min_ratio = min(ratios)
        max_ratio = max(ratios)

        trend_arrow = "→"
        if len(ratios) >= 2:
            if ratios[-1] > ratios[-2]:
                trend_arrow = "↑"
            elif ratios[-1] < ratios[-2]:
                trend_arrow = "↓"

        spark = _sparkline(ratios, width=min(40, len(ratios)))

        ts = latest.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        lines = [
            "=" * 62,
            "Gold/Silver Ratio Tracker",
            "=" * 62,
            f"Last update : {ts}",
            f"Gold ({latest.gold.symbol:>5}) : {latest.gold.price:,.4f}",
            f"Silver ({latest.silver.symbol:>5}) : {latest.silver.price:,.4f}",
            f"Ratio (G/S) : {latest.ratio:.6f}  {trend_arrow}",
            f"Window stats: min={min_ratio:.6f} max={max_ratio:.6f} avg={mean_ratio:.6f}",
            f"Trend      : {spark}",
            "=" * 62,
        ]
        return "\n".join(lines)


def _sparkline(values: list[float], width: int = 20) -> str:
    if not values:
        return ""

    blocks = "▁▂▃▄▅▆▇█"

    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values

    low = min(sampled)
    high = max(sampled)
    span = high - low
    if span == 0:
        return blocks[0] * len(sampled)

    chars = []
    for value in sampled:
        norm = (value - low) / span
        idx = min(int(norm * (len(blocks) - 1)), len(blocks) - 1)
        chars.append(blocks[idx])
    return "".join(chars)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track the gold/silver ratio.")
    parser.add_argument("--gold-symbol", default="XAUUSD", help="Gold symbol (normalized to XAUUSD)")
    parser.add_argument("--silver-symbol", default="XAGUSD", help="Silver symbol (normalized to XAGUSD)")
    parser.add_argument(
        "--provider",
        default="stooq",
        choices=["yahoo", "stooq", "google", "twelve", "metalsapi", "polygon"],
        help="Primary price provider",
    )
    parser.add_argument(
        "--fallback-provider",
        default="none",
        choices=["none", "yahoo", "stooq", "google", "twelve", "metalsapi", "polygon"],
        help="Fallback provider if primary fails",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Refresh interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--points",
        type=int,
        default=120,
        help="Number of historical points to keep in memory",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Fetch and print a single snapshot, then exit",
    )
    return parser.parse_args(argv)


def run(argv: list[str]) -> int:
    args = parse_args(argv)

    provider = create_provider_chain(args.provider, args.fallback_provider)
    tracker = RatioTracker(
        provider=provider,
        gold_symbol=normalize_symbol(args.gold_symbol),
        silver_symbol=normalize_symbol(args.silver_symbol),
        max_points=args.points,
    )

    if args.once:
        tracker.refresh()
        print(tracker.render())
        return 0

    while True:
        try:
            tracker.refresh()
            print("\033[2J\033[H", end="")
            print(tracker.render())
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
        except requests.RequestException as exc:
            print(f"Network/API error: {exc}", file=sys.stderr)
            time.sleep(max(args.interval, 5.0))
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}", file=sys.stderr)
            time.sleep(max(args.interval, 5.0))


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
