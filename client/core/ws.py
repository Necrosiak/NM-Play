"""
NM-Play — WebSocket client
Real-time lobby/player updates from the relay server.
"""

import json
import threading
import time

try:
    import websocket
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False

from core.config import WS_URL as NM_WS


class NMWebSocket:
    def __init__(self):
        self.ws = None
        self.connected = False
        self.callbacks = {}
        self._thread = None
        self._reconnect = True

    def on(self, event: str, callback):
        self.callbacks[event] = callback
        return self

    def _dispatch(self, event: str, data):
        cb = self.callbacks.get(event) or self.callbacks.get("*")
        if cb:
            cb(event, data)

    def connect(self):
        if not WS_AVAILABLE:
            print("[WS] websocket-client not installed, skipping realtime updates")
            return
        self._reconnect = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while self._reconnect:
            try:
                self.ws = websocket.WebSocketApp(
                    NM_WS,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                self.ws.run_forever()
            except Exception as e:
                print(f"[WS] Error: {e}")
            if self._reconnect:
                print("[WS] Reconnecting in 5s...")
                time.sleep(5)

    def _on_open(self, ws):
        self.connected = True
        print("[WS] Connected")
        self._dispatch("connect", {})

    def _on_message(self, ws, message):
        try:
            msg = json.loads(message)
            self._dispatch(msg.get("event", "unknown"), msg.get("data", {}))
        except Exception:
            pass

    def _on_error(self, ws, error):
        print(f"[WS] Error: {error}")

    def _on_close(self, ws, code, msg):
        self.connected = False
        self._dispatch("disconnect", {})

    def disconnect(self):
        self._reconnect = False
        if self.ws:
            self.ws.close()
