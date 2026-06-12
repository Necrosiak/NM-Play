"""
NM-Play — Relay Manager
Manages the lan-play tunnel process for each platform.
"""

import os
import sys
import platform
import subprocess
import threading

from core.config import RELAY_HOST, RELAY_PORT

def _get_base_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BIN_DIR = os.path.join(_get_base_dir(), "bin") if not getattr(sys, "frozen", False) else _get_base_dir()

def get_lanplay_bin() -> str:
    if platform.system() == "Windows":
        return os.path.join(BIN_DIR, "lan-play.exe")
    elif platform.system() == "Darwin":
        return os.path.join(BIN_DIR, "lan-play-macos")
    else:
        return os.path.join(BIN_DIR, "lan-play")


class RelayManager:
    def __init__(self, log_callback=None):
        self.process     = None
        self.running     = False
        self.log_cb      = log_callback or print
        self.platform_id = "switch"
        self.lan_ip      = "10.13.1.2"

    def set_platform(self, platform_id: str, lan_ip: str = "10.13.1.2"):
        self.platform_id = platform_id
        self.lan_ip      = lan_ip

    def connect(self) -> bool:
        binary = get_lanplay_bin()
        if not os.path.exists(binary):
            self.log_cb(f"ERROR: lan-play binary not found: {binary}")
            return False

        if platform.system() != "Windows":
            os.chmod(binary, 0o755)

        cmd = [binary, "--relay-server-addr", f"{RELAY_HOST}:{RELAY_PORT}"]
        if self.lan_ip:
            cmd += ["--fake-internet", "--ip", f"{self.lan_ip}/16"]

        self.log_cb(f"Connecting: {' '.join(cmd)}")
        try:
            kw = {}
            if platform.system() == "Windows":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, **kw
            )
            self.running = True
            threading.Thread(target=self._read_output, daemon=True).start()
            return True
        except PermissionError:
            self.log_cb("ERROR: Run as Administrator (required for Npcap/libpcap)")
            return False
        except Exception as e:
            self.log_cb(f"ERROR: {e}")
            return False

    def disconnect(self):
        if self.process:
            self.process.terminate()
            self.process = None
        self.running = False
        self.log_cb("Disconnected from relay.")

    def _read_output(self):
        if not self.process:
            return
        for line in self.process.stdout:
            line = line.rstrip()
            if line:
                self.log_cb(f"  {line}")
        self.running = False
