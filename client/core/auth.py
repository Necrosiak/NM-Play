"""
NM-Play — NM.com Authentication
Login with NetworkMemories account.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import hashlib
import os

NM_AUTH_URL = "https://networkmemories.com/api/auth"
TOKEN_FILE  = os.path.join(os.path.expanduser("~"), ".nmplay_token")


class NMAuth:
    def __init__(self):
        self.token    = None
        self.username = None
        self.user_id  = None
        self.avatar   = None
        self._load_token()

    def _load_token(self):
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE) as f:
                    data = json.load(f)
                    self.token    = data.get("token")
                    self.username = data.get("username")
                    self.user_id  = data.get("user_id")
                    self.avatar   = data.get("avatar")
        except Exception:
            pass

    def _save_token(self):
        try:
            with open(TOKEN_FILE, "w") as f:
                json.dump({
                    "token":    self.token,
                    "username": self.username,
                    "user_id":  self.user_id,
                    "avatar":   self.avatar
                }, f)
        except Exception:
            pass

    def login(self, username: str, password: str) -> tuple[bool, str]:
        """Login with NM credentials. Returns (success, message)."""
        try:
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            body = json.dumps({"username": username, "password": pw_hash}).encode()
            req = urllib.request.Request(
                f"{NM_AUTH_URL}/login",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                self.token    = data.get("token")
                self.username = data.get("username", username)
                self.user_id  = data.get("user_id")
                self.avatar   = data.get("avatar")
                self._save_token()
                return True, f"Welcome, {self.username}!"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "Invalid username or password."
            return False, f"Server error ({e.code})"
        except Exception as e:
            return False, f"Connection error: {e}"

    def logout(self):
        self.token = self.username = self.user_id = self.avatar = None
        try:
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
        except Exception:
            pass

    def is_logged_in(self) -> bool:
        return self.token is not None

    def validate_token(self) -> bool:
        """Validate stored token against NM server."""
        if not self.token:
            return False
        try:
            req = urllib.request.Request(
                f"{NM_AUTH_URL}/validate",
                headers={"Authorization": f"Bearer {self.token}"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return data.get("valid", False)
        except Exception:
            return False
