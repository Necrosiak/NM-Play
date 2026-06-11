"""
NM-Play — API Client
Communicates with the NM-Play relay server REST API.
"""

import json
import urllib.request
import urllib.error
from typing import Optional

NM_SERVER = "networkmemories.com"
API_BASE  = f"http://{NM_SERVER}:8080"


def _request(method: str, path: str, data: dict = None, token: str = None) -> Optional[dict]:
    url = f"{API_BASE}{path}"
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"[API] HTTP {e.code}: {path}")
        return None
    except Exception as e:
        print(f"[API] Error {path}: {e}")
        return None


def get_health() -> bool:
    r = _request("GET", "/health")
    return r is not None and r.get("status") == "ok"

def get_stats() -> dict:
    return _request("GET", "/stats") or {}

def get_lobbies(platform: str = "") -> list:
    path = "/lobbies"
    if platform:
        path += f"?platform={platform}"
    return _request("GET", path) or []

def create_lobby(name: str, game: str, platform: str, username: str, max_players: int = 8) -> Optional[dict]:
    return _request("POST", "/lobbies", {
        "name": name, "game": game, "platform": platform,
        "username": username, "max_players": max_players
    })

def join_lobby(lobby_id: str, username: str, platform: str) -> Optional[dict]:
    return _request("POST", f"/lobbies/{lobby_id}/join", {
        "username": username, "platform": platform
    })
