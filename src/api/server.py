"""
BTC Trade Engine API — Daemon Thread Launcher
==============================================
Starts uvicorn + the FastAPI app in a daemon thread so it runs alongside
the ITM without blocking the ITM's event loop or main thread.

Usage
-----
::

    from src.api.server import APIServer

    server = APIServer(host="0.0.0.0", port=8765)
    server.start()   # non-blocking; returns immediately
    # ...
    server.stop()    # graceful shutdown

Environment overrides
---------------------
BTE_API_HOST   Listen host  (default: 0.0.0.0)
BTE_API_PORT   Listen port  (default: 8765)
BTE_API_LOG    Log level    (default: warning)
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

import uvicorn

logger = logging.getLogger(__name__)

_DEFAULT_HOST = os.environ.get("BTE_API_HOST", "0.0.0.0")
_DEFAULT_PORT = int(os.environ.get("BTE_API_PORT", "8765"))
_DEFAULT_LOG_LEVEL = os.environ.get("BTE_API_LOG", "warning")


class APIServer:
    """Wraps uvicorn in a daemon thread.

    The thread is marked daemon=True so it is killed automatically when the
    main process exits — no explicit shutdown is required for clean process
    termination.  Call ``stop()`` for a graceful drain during normal shutdown.
    """

    def __init__(
        self,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
        log_level: str = _DEFAULT_LOG_LEVEL,
    ) -> None:
        self._host = host
        self._port = port
        self._log_level = log_level
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the API server in a background daemon thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("APIServer.start() called but server is already running")
            return

        config = uvicorn.Config(
            app="src.api.app:app",
            host=self._host,
            port=self._port,
            log_level=self._log_level,
            loop="asyncio",
            # No reload — we're embedded, not a development server
            reload=False,
            # Use a single worker; the ITM owns process-level concurrency
            workers=None,
        )
        self._server = uvicorn.Server(config=config)

        self._thread = threading.Thread(
            target=self._server.run,
            name="bte-api-server",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "BTE API server started on http://%s:%d (daemon thread)",
            self._host,
            self._port,
        )

    def stop(self) -> None:
        """Signal uvicorn to shut down and wait for the thread to exit."""
        if self._server is None:
            return
        self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                logger.warning("BTE API server thread did not exit within 10s")
        logger.info("BTE API server stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"
