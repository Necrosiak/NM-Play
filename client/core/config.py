"""
NM-Play — Configuration
Edit this file or use environment variables to configure your server.
For the official NetworkMemories release, these values are pre-configured.
"""

import os

# Relay server address
RELAY_HOST = os.environ.get("NM_RELAY_HOST", "localhost")
RELAY_PORT = int(os.environ.get("NM_RELAY_PORT", "11451"))

# API server
API_HOST = os.environ.get("NM_API_HOST", "localhost")
API_PORT = int(os.environ.get("NM_API_PORT", "8080"))
API_BASE = f"http://{API_HOST}:{API_PORT}"
WS_URL   = f"ws://{API_HOST}:{API_PORT}/ws"

# Auth server
AUTH_URL = os.environ.get("NM_AUTH_URL", "")

# App info
APP_NAME    = "NM-Play"
APP_VERSION = "1.0.0"