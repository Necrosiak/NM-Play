"""
NM-Play — Auth via OAuth-style browser login
Le client ouvre le navigateur → user se connecte sur NM → token retourné via nmplay://
"""

import json
import os
import threading
import webbrowser
import urllib.request
import urllib.error
import urllib.parse
import http.server
import socket
from core.config import AUTH_URL

TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".nmplay_token")
NM_AUTH_PAGE = f"{AUTH_URL}/auth/nmplay"
NM_VALIDATE  = f"{AUTH_URL}/api/nmplay/validate"
NM_TOKEN_API = f"{AUTH_URL}/api/nmplay/token"


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

    def login_browser(self, callback=None) -> bool:
        """
        Ouvre le navigateur vers NM auth page.
        Lance un serveur local temporaire pour capturer le callback nmplay://
        """
        received = {"token": None, "username": None}

        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                received["token"]    = params.get("token", [None])[0]
                received["username"] = params.get("username", [None])[0]
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"""<html><body style="background:#0f0f1a;color:#eaeaea;font-family:sans-serif;text-align:center;padding:60px">
                <h2 style="color:#e94560">NM-Play</h2>
                <p>Connexion reussie ! Vous pouvez fermer cette fenetre.</p>
                <script>window.close();</script></body></html>""")
            def log_message(self, *args):
                pass

        # Trouver un port libre
        s = socket.socket()
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()

        server = http.server.HTTPServer(("localhost", port), CallbackHandler)

        def _serve():
            server.handle_request()

        t = threading.Thread(target=_serve, daemon=True)
        t.start()

        # Ouvrir le navigateur avec callback vers localhost
        auth_url = f"{NM_AUTH_PAGE}?callback=http://localhost:{port}"
        webbrowser.open(auth_url)

        t.join(timeout=120)  # 2 minutes max

        if received["token"]:
            # Echanger le one-time token contre un token permanent
            try:
                body = json.dumps({"token": received["token"]}).encode()
                req  = urllib.request.Request(
                    NM_TOKEN_API,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                    self.token    = data.get("token")
                    self.username = data.get("username", received["username"])
                    self.user_id  = data.get("user_id")
                    self.avatar   = data.get("avatar")
                    self._save_token()
                    if callback:
                        callback(True, f"Connecte en tant que {self.username}")
                    return True
            except Exception as e:
                if callback:
                    callback(False, f"Erreur: {e}")
                return False

        if callback:
            callback(False, "Connexion annulee ou timeout.")
        return False

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
        if not self.token:
            return False
        try:
            req = urllib.request.Request(
                NM_VALIDATE,
                headers={"Authorization": f"Bearer {self.token}"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                if data.get("token"):
                    self.token = data["token"]
                    self._save_token()
                return data.get("valid", False)
        except Exception:
            return False