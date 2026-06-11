"""
NM-Play — Network Scanner
Detects consoles and emulators on the local network via MAC address OUI lookup.
"""

import socket
import subprocess
import platform
import re
import threading
from dataclasses import dataclass, field
from typing import Optional

# MAC OUI prefixes by manufacturer/console
OUI_MAP = {
    # Nintendo
    "00:09:BF": "Nintendo",
    "00:17:AB": "Nintendo",
    "00:19:1D": "Nintendo",
    "00:1A:E9": "Nintendo",
    "00:1B:EA": "Nintendo",
    "00:1F:C5": "Nintendo",
    "00:21:47": "Nintendo",
    "00:22:D7": "Nintendo",
    "00:24:44": "Nintendo",
    "34:AF:2C": "Nintendo",
    "40:F4:07": "Nintendo",
    "58:BD:A3": "Nintendo",
    "7C:BB:8A": "Nintendo",
    "8C:56:C5": "Nintendo",
    "98:B6:E9": "Nintendo",
    "A4:C0:E1": "Nintendo",
    "B8:AE:6E": "Nintendo",
    "CC:FB:65": "Nintendo",
    "E0:E7:51": "Nintendo",
    # Sony PlayStation
    "00:13:A9": "Sony",
    "00:1D:0D": "Sony",
    "00:24:BE": "Sony",
    "00:D9:D1": "Sony",
    "28:0D:FC": "Sony",
    "40:49:0F": "Sony",
    "70:9E:29": "Sony",
    "AC:9B:0A": "Sony",
    "BC:60:A7": "Sony",
    "F8:46:1C": "Sony",
    # Microsoft Xbox
    "00:50:F2": "Microsoft",
    "28:18:78": "Microsoft",
    "60:45:CB": "Microsoft",
    "7C:1E:52": "Microsoft",
    "98:5F:D3": "Microsoft",
    "C8:3D:D4": "Microsoft",
    # Valve Steam Deck
    "A4:AE:11": "Valve",
}

# Console detection by OUI + context
CONSOLE_BY_OUI = {
    "Nintendo": {
        "detect": ["Switch", "Wii U", "3DS", "Wii"],
        "default": "Nintendo Switch"
    },
    "Sony": {
        "detect": ["PS4", "PS5", "PS3", "PSP", "PS Vita"],
        "default": "PlayStation"
    },
    "Microsoft": {
        "detect": ["Xbox One", "Xbox 360", "Xbox Series"],
        "default": "Xbox"
    },
    "Valve": {
        "default": "Steam Deck"
    }
}


@dataclass
class DetectedDevice:
    mac: str
    ip: str
    manufacturer: str = "Unknown"
    console_type: str = "Unknown"
    hostname: str = ""
    custom_name: str = ""
    nm_user: str = ""
    is_emulator: bool = False
    emulator_name: str = ""


def get_oui(mac: str) -> str:
    """Extract OUI (first 3 bytes) from MAC address."""
    parts = mac.upper().replace("-", ":").split(":")
    if len(parts) < 3:
        return ""
    return ":".join(parts[:3])


def identify_device(mac: str) -> tuple[str, str]:
    """Returns (manufacturer, console_type) from MAC OUI."""
    oui = get_oui(mac)
    manufacturer = OUI_MAP.get(oui, "Unknown")
    if manufacturer == "Unknown":
        return manufacturer, "Unknown"
    info = CONSOLE_BY_OUI.get(manufacturer, {})
    return manufacturer, info.get("default", "Unknown")


def get_arp_table() -> list[dict]:
    """Parse ARP table to find devices on local network."""
    devices = []
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("arp -a", shell=True).decode("utf-8", errors="ignore")
            pattern = r"(\d+\.\d+\.\d+\.\d+)\s+([\da-fA-F-]{17})\s+\w+"
        else:
            output = subprocess.check_output(["arp", "-a"], stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
            pattern = r"\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([\da-fA-F:]{17})"

        for match in re.finditer(pattern, output):
            ip = match.group(1)
            mac = match.group(2).replace("-", ":").upper()
            manufacturer, console_type = identify_device(mac)
            devices.append({
                "ip": ip,
                "mac": mac,
                "manufacturer": manufacturer,
                "console_type": console_type
            })
    except Exception as e:
        print(f"[Network] ARP scan error: {e}")
    return devices


def ping_subnet(base_ip: str, count: int = 254):
    """Ping entire subnet to populate ARP table."""
    parts = base_ip.split(".")
    if len(parts) < 3:
        return
    subnet = ".".join(parts[:3])

    def _ping(ip):
        try:
            if platform.system() == "Windows":
                subprocess.run(["ping", "-n", "1", "-w", "200", ip],
                               capture_output=True, timeout=1)
            else:
                subprocess.run(["ping", "-c", "1", "-W", "1", ip],
                               capture_output=True, timeout=1)
        except Exception:
            pass

    threads = []
    for i in range(1, count + 1):
        ip = f"{subnet}.{i}"
        t = threading.Thread(target=_ping, args=(ip,), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=2)


def get_local_ip() -> str:
    """Get local machine IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def scan_network(callback=None) -> list[DetectedDevice]:
    """
    Full network scan:
    1. Get local IP
    2. Ping subnet to populate ARP
    3. Parse ARP table
    4. Identify consoles by MAC OUI
    """
    local_ip = get_local_ip()
    print(f"[Network] Local IP: {local_ip}, scanning subnet...")

    ping_subnet(local_ip)

    raw = get_arp_table()
    devices = []

    for d in raw:
        device = DetectedDevice(
            mac=d["mac"],
            ip=d["ip"],
            manufacturer=d["manufacturer"],
            console_type=d["console_type"]
        )
        # Try reverse DNS
        try:
            device.hostname = socket.gethostbyaddr(d["ip"])[0]
        except Exception:
            pass

        devices.append(device)
        if callback:
            callback(device)

    print(f"[Network] Found {len(devices)} devices ({sum(1 for d in devices if d.manufacturer != 'Unknown')} consoles)")
    return devices


# Known emulator process names
EMULATOR_PROCESSES = {
    "dolphin.exe":    ("Dolphin",  "gamecube"),
    "dolphin-emu":    ("Dolphin",  "gamecube"),
    "pcsx2.exe":      ("PCSX2",    "ps2"),
    "pcsx2-qt.exe":   ("PCSX2",    "ps2"),
    "rpcs3.exe":      ("RPCS3",    "ps3"),
    "xemu.exe":       ("Xemu",     "xbox"),
    "xenia.exe":      ("Xenia",    "xbox360"),
    "xenia_canary.exe":("Xenia",   "xbox360"),
    "ryujinx.exe":    ("Ryujinx",  "switch"),
    "ryujinx":        ("Ryujinx",  "switch"),
    "ppsspp.exe":     ("PPSSPP",   "psp"),
    "ppsspp":         ("PPSSPP",   "psp"),
    "vita3k.exe":     ("Vita3k",   "vita"),
}


def detect_emulators() -> list[dict]:
    """Detect running emulators by process name."""
    found = []
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("tasklist /fo csv /nh", shell=True).decode("utf-8", errors="ignore")
            running = [line.split(",")[0].strip('"').lower() for line in output.splitlines()]
        else:
            output = subprocess.check_output(["ps", "-e", "-o", "comm="], stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
            running = [line.strip().lower() for line in output.splitlines()]

        for proc, (name, platform_id) in EMULATOR_PROCESSES.items():
            if proc.lower() in running:
                found.append({"name": name, "platform": platform_id, "process": proc})
    except Exception as e:
        print(f"[Network] Emulator detection error: {e}")
    return found
