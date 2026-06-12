"""
NM-Play API client
"""
import urllib.request
import urllib.error
import json
from core.config import API_BASE

class NMPlayAPI:
    def __init__(self, base_url=API_BASE):
        self.base = base_url

    def _get(self, path, token=None):
        req = urllib.request.Request(f"{self.base}{path}")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read())
        except Exception as e:
            print(f"[API] Error {path}: {e}")
            return None

    def _post(self, path, data=None, token=None):
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(
            f"{self.base}{path}", data=body,
            headers={"Content-Type": "application/json"},
            method="POST")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read())
            except Exception:
                return {"error": str(e)}
        except Exception as e:
            print(f"[API] Error {path}: {e}")
            return None

    def health(self):
        return self._get("/health")

    def stats(self):
        return self._get("/stats")

    def get_lobbies(self, platform=""):
        path = f"/lobbies?platform={platform}" if platform else "/lobbies"
        return self._get(path) or []

    def connect(self, platform, token, lan_ip="", username=""):
        return self._post("/connect", {"platform": platform, "lan_ip": lan_ip, "username": username}, token)

    def disconnect(self, token):
        return self._post("/disconnect", {}, token)

    def heartbeat(self, token):
        return self._post("/heartbeat", {}, token)

    def create_lobby(self, name, platform, game="", password="", max_players=8, token=None, username=""):
        return self._post("/lobbies", {
            "name": name, "platform": platform,
            "game": game, "password": password,
            "maxPlayers": max_players,
            "username": username
        }, token)

    def join_lobby(self, lobby_id, password="", token=None, username=""):
        return self._post(f"/lobbies/{lobby_id}/join", {"password": password, "username": username}, token)

    def leave_lobby(self, token, lobby_id=""):
        if lobby_id:
            return self._post(f"/lobbies/{lobby_id}/leave", {}, token)
        return self._post("/lobbies/current/leave", {}, token)