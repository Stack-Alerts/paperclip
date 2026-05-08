"""
ITM Section G — Binance USDT-M Futures REST + WebSocket Client
================================================================
Provides:
  1. Authenticated REST client (HMAC-SHA256 signed requests) targeting the
     Binance USDT-M Futures **testnet** by default.
  2. WebSocket user-data stream for real-time ``executionReport`` and
     ``ACCOUNT_UPDATE`` events.

IMPORTANT — Safety
------------------
* Testnet URLs are used by default.  Set ``use_testnet=False`` ONLY for
  production mainnet after explicit CTO sign-off.
* Never commit API keys.  Pass them via environment variables:
  ``BINANCE_TESTNET_API_KEY`` / ``BINANCE_TESTNET_API_SECRET``

Rate limiting
-------------
Weight tracking is handled by the companion ``RateLimiter``.  This client
calls ``limiter.consume(weight)`` before every REST call and raises
``RateLimitExceeded`` if the budget is exhausted.

Error handling
--------------
Binance-specific error codes are mapped to ``BinanceError`` subclasses:
  - ``InsufficientMarginError``  (code -2019)
  - ``InvalidLotSizeError``      (code -1111)
  - ``MinNotionalError``         (code -1013)
  - ``OrderNotFoundError``       (code -2011)
  - Generic ``BinanceApiError``  for all other codes

Usage
-----
::

    client = BinanceClient.from_env(use_testnet=True)
    exch_id = client.place_order(spec)
    client.cancel_order(spec.client_order_id)
    client.start_user_data_stream(on_execution_report, on_account_update)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import threading
import time
import urllib.parse
from decimal import Decimal
from typing import Callable, Optional

try:
    import requests  # type: ignore
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

try:
    import websocket  # type: ignore  (websocket-client)
    _WS_AVAILABLE = True
except ImportError:
    _WS_AVAILABLE = False

from .order_factory import OrderSpec
from .rate_limiter import RateLimiter, RateLimitExceeded

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Binance testnet / mainnet URLs
# ---------------------------------------------------------------------------

TESTNET_REST_BASE = "https://testnet.binancefuture.com"
MAINNET_REST_BASE = "https://fapi.binance.com"
TESTNET_WS_BASE   = "wss://stream.binancefuture.com"
MAINNET_WS_BASE   = "wss://fstream.binance.com"


# ---------------------------------------------------------------------------
# Binance error taxonomy
# ---------------------------------------------------------------------------


class BinanceError(Exception):
    """Base class for all Binance API errors."""
    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"Binance error {code}: {message}")
        self.code = code
        self.binance_message = message


class InsufficientMarginError(BinanceError):
    """Raised when Binance returns code -2019 (insufficient margin)."""


class InvalidLotSizeError(BinanceError):
    """Raised when Binance returns code -1111 (invalid lot size)."""


class MinNotionalError(BinanceError):
    """Raised when Binance returns code -1013 / filter MIN_NOTIONAL failed."""


class OrderNotFoundError(BinanceError):
    """Raised when Binance returns code -2011 (order not found)."""


class BinanceApiError(BinanceError):
    """Generic Binance API error."""


def _raise_binance_error(code: int, msg: str) -> None:
    mapping = {
        -2019: InsufficientMarginError,
        -1111: InvalidLotSizeError,
        -1013: MinNotionalError,
        -2011: OrderNotFoundError,
    }
    exc_cls = mapping.get(code, BinanceApiError)
    raise exc_cls(code, msg)


# ---------------------------------------------------------------------------
# BinanceClient
# ---------------------------------------------------------------------------


class BinanceClient:
    """Authenticated Binance USDT-M Futures REST + WebSocket client.

    Parameters
    ----------
    api_key:     Binance API key (read from env when not provided)
    api_secret:  Binance API secret (read from env when not provided)
    use_testnet: Target testnet (True) or mainnet (False). Default True.
    rate_limiter:``RateLimiter`` instance; one is created if not provided.
    session:     ``requests.Session`` — injected for testing.
    """

    REST_WEIGHTS = {
        "POST /fapi/v1/order": 1,
        "DELETE /fapi/v1/order": 1,
        "POST /fapi/v1/listenKey": 1,
        "PUT /fapi/v1/listenKey": 1,
    }

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        use_testnet: bool = True,
        rate_limiter: Optional[RateLimiter] = None,
        session=None,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty")
        self._api_key = api_key
        self._api_secret = api_secret
        self._rest_base = TESTNET_REST_BASE if use_testnet else MAINNET_REST_BASE
        self._ws_base = TESTNET_WS_BASE if use_testnet else MAINNET_WS_BASE
        self._rate_limiter = rate_limiter or RateLimiter()

        if session is None and _REQUESTS_AVAILABLE:
            import requests as req
            self._session = req.Session()
        else:
            self._session = session  # allows mock injection in tests

        self._listen_key: Optional[str] = None
        self._ws_thread: Optional[threading.Thread] = None

        logger.info(
            "BinanceClient initialised: testnet=%s rest_base=%s",
            use_testnet, self._rest_base,
        )

    @classmethod
    def from_env(cls, use_testnet: bool = True) -> "BinanceClient":
        """Construct from environment variables.

        Reads:
          ``BINANCE_TESTNET_API_KEY`` / ``BINANCE_TESTNET_API_SECRET``
          ``BINANCE_MAINNET_API_KEY`` / ``BINANCE_MAINNET_API_SECRET``
        """
        if use_testnet:
            key = os.environ.get("BINANCE_TESTNET_API_KEY", "")
            secret = os.environ.get("BINANCE_TESTNET_API_SECRET", "")
        else:
            key = os.environ.get("BINANCE_MAINNET_API_KEY", "")
            secret = os.environ.get("BINANCE_MAINNET_API_SECRET", "")
        if not key or not secret:
            env_prefix = "BINANCE_TESTNET" if use_testnet else "BINANCE_MAINNET"
            raise EnvironmentError(
                f"{env_prefix}_API_KEY and {env_prefix}_API_SECRET must be set"
            )
        return cls(api_key=key, api_secret=secret, use_testnet=use_testnet)

    # ------------------------------------------------------------------ #
    # Order placement                                                      #
    # ------------------------------------------------------------------ #

    def place_order(self, spec: OrderSpec) -> str:
        """Place an order on Binance Futures.

        Parameters
        ----------
        spec:  ``OrderSpec`` from the order factory

        Returns
        -------
        str
            Binance exchange order ID (``orderId`` as string).

        Raises
        ------
        BinanceError subclasses on exchange errors.
        RateLimitExceeded if rate budget is exhausted.
        """
        params = spec.to_binance_params()
        self._rate_limiter.consume(
            weight=self.REST_WEIGHTS.get("POST /fapi/v1/order", 1),
        )
        response = self._signed_request(
            method="POST",
            path="/fapi/v1/order",
            params=params,
        )
        exchange_id = str(response.get("orderId", ""))
        logger.info(
            "BinanceClient place_order: cid=%r exchange_id=%r type=%s qty=%s",
            spec.client_order_id, exchange_id,
            spec.binance_type.value, spec.quantity,
        )
        return exchange_id

    def cancel_order(self, client_order_id: str, symbol: str = "BTCUSDT") -> bool:
        """Cancel an order by clientOrderId.

        Returns True if cancelled, False if it was already filled/missing.
        """
        self._rate_limiter.consume(
            weight=self.REST_WEIGHTS.get("DELETE /fapi/v1/order", 1),
        )
        try:
            self._signed_request(
                method="DELETE",
                path="/fapi/v1/order",
                params={
                    "symbol": symbol,
                    "origClientOrderId": client_order_id,
                },
            )
            logger.info(
                "BinanceClient cancel_order: cid=%r ✓", client_order_id
            )
            return True
        except OrderNotFoundError:
            logger.warning(
                "BinanceClient cancel_order: order %r not found (already filled?)",
                client_order_id,
            )
            return False

    # ------------------------------------------------------------------ #
    # User-data WebSocket stream                                           #
    # ------------------------------------------------------------------ #

    def start_user_data_stream(
        self,
        on_execution_report: Callable[[dict], None],
        on_account_update: Optional[Callable[[dict], None]] = None,
    ) -> None:
        """Start the user-data WebSocket stream in a background thread.

        Parameters
        ----------
        on_execution_report:
            Called for each ``executionReport`` event with the raw payload dict.
        on_account_update:
            Called for each ``ACCOUNT_UPDATE`` event (optional).
        """
        if not _WS_AVAILABLE:
            raise ImportError(
                "websocket-client is required for start_user_data_stream. "
                "Install it with: pip install websocket-client"
            )
        self._listen_key = self._create_listen_key()
        ws_url = f"{self._ws_base}/ws/{self._listen_key}"

        def on_message(ws, raw_msg):
            import json
            try:
                payload = json.loads(raw_msg)
                event_type = payload.get("e")
                if event_type == "ORDER_TRADE_UPDATE":
                    # Futures-specific wrapper
                    on_execution_report(payload.get("o", payload))
                elif event_type == "executionReport":
                    on_execution_report(payload)
                elif event_type == "ACCOUNT_UPDATE" and on_account_update:
                    on_account_update(payload)
                else:
                    logger.debug("WS unhandled event: %s", event_type)
            except Exception:
                logger.exception("WS on_message handler raised")

        def on_error(ws, error):
            logger.error("WS error: %s", error)

        def on_close(ws, close_status_code, close_msg):
            logger.warning(
                "WS closed: status=%s msg=%s", close_status_code, close_msg
            )

        def on_open(ws):
            logger.info("User-data WebSocket stream opened: %s", ws_url)

        ws_app = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )

        def _run():
            ws_app.run_forever(ping_interval=60, ping_timeout=10)

        self._ws_thread = threading.Thread(target=_run, daemon=True, name="binance-ws")
        self._ws_thread.start()
        logger.info("User-data WebSocket stream started (thread: binance-ws)")

    def keep_alive_listen_key(self) -> None:
        """Extend the listen key TTL (call every 30–60 minutes)."""
        if not self._listen_key:
            return
        self._signed_request(
            method="PUT",
            path="/fapi/v1/listenKey",
            params={"listenKey": self._listen_key},
        )
        logger.debug("Listen key keep-alive sent")

    # ------------------------------------------------------------------ #
    # Signed request helper                                                #
    # ------------------------------------------------------------------ #

    def _signed_request(self, method: str, path: str, params: dict) -> dict:
        """Execute an HMAC-SHA256 signed REST request.

        Parameters
        ----------
        method:  HTTP method ("GET", "POST", "DELETE", "PUT")
        path:    API path (e.g. "/fapi/v1/order")
        params:  dict of query/body parameters (excluding signature)

        Returns
        -------
        dict
            Parsed JSON response body.

        Raises
        ------
        BinanceError subclass on exchange-level errors.
        requests.HTTPError on non-JSON HTTP errors.
        RateLimitExceeded if the rate budget is already exhausted.
        """
        params["timestamp"] = str(int(time.time() * 1000))
        params["recvWindow"] = "5000"

        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature

        url = f"{self._rest_base}{path}"
        headers = {"X-MBX-APIKEY": self._api_key}

        if method in ("GET", "DELETE"):
            resp = self._session.request(method, url, params=params, headers=headers)
        else:
            resp = self._session.request(method, url, data=params, headers=headers)

        # Handle rate-limit responses before raising for status
        if resp.status_code in (429, 418):
            retry_after = int(resp.headers.get("Retry-After", 60))
            logger.error(
                "Binance rate limit response %d — backing off %ds",
                resp.status_code, retry_after,
            )
            self._rate_limiter.on_rate_limit_response(resp.status_code, retry_after)
            raise RateLimitExceeded(
                f"Binance HTTP {resp.status_code}: back off for {retry_after}s"
            )

        try:
            body = resp.json()
        except Exception:
            resp.raise_for_status()
            raise

        if isinstance(body, dict) and "code" in body and body["code"] < 0:
            code = body["code"]
            msg = body.get("msg", "")
            logger.error(
                "Binance API error: path=%s code=%d msg=%s", path, code, msg
            )
            _raise_binance_error(code, msg)

        resp.raise_for_status()
        return body

    def _create_listen_key(self) -> str:
        """Request a new listen key from Binance."""
        self._rate_limiter.consume(
            weight=self.REST_WEIGHTS.get("POST /fapi/v1/listenKey", 1),
        )
        response = self._signed_request(
            method="POST",
            path="/fapi/v1/listenKey",
            params={},
        )
        key = response.get("listenKey", "")
        logger.info("Binance listen key created: %s…", key[:8])
        return key
