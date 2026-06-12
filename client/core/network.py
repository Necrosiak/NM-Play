"""
NM-Play — Network Scanner
Detects consoles and emulators on the local network via MAC address OUI lookup.
"Reviving the past, connecting the present." — NerdHz & Nekyron / NetworkMemories
"""

import socket
import subprocess
import platform
import re
import threading
from dataclasses import dataclass
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

# MAC OUI -> console type direct mapping
OUI_MAP = {
    # Nintendo Switch / Switch 2
    "00:09:BF": "Nintendo Switch", "00:17:AB": "Nintendo Switch",
    "00:19:1D": "Nintendo Switch", "00:1A:E9": "Nintendo Switch",
    "00:1B:EA": "Nintendo Switch", "00:1F:C5": "Nintendo Switch",
    "00:21:47": "Nintendo Switch", "00:22:D7": "Nintendo Switch",
    "00:24:44": "Nintendo Switch", "34:AF:2C": "Nintendo Switch",
    "40:F4:07": "Nintendo Switch", "58:BD:A3": "Nintendo Switch",
    "7C:BB:8A": "Nintendo Switch", "8C:56:C5": "Nintendo Switch",
    "98:B6:E9": "Nintendo Switch", "A4:C0:E1": "Nintendo Switch",
    "B8:AE:6E": "Nintendo Switch", "CC:FB:65": "Nintendo Switch",
    "E0:E7:51": "Nintendo Switch",
    # Sony PS2
    "00:04:1F": "PS2", "00:13:15": "PS2", "00:19:C5": "PS2",
    "00:1F:A7": "PS2", "04:F7:78": "PS2", "0C:FE:45": "PS2",
    "28:40:DD": "PS2", "70:9E:29": "PS2", "78:C8:81": "PS2",
    "F8:46:1C": "PS2",
    # Sony PS3
    "00:1D:0D": "PS3", "00:24:8D": "PS3", "00:D9:D1": "PS3",
    "28:0D:FC": "PS3", "2C:9E:00": "PS3", "2C:CC:44": "PS3",
    "70:66:2A": "PS3", "BC:33:29": "PS3", "BC:60:A7": "PS3",
    "C8:4A:A0": "PS3", "C8:63:F1": "PS3", "F4:64:12": "PS3",
    "00:13:A9": "PS3", "00:24:BE": "PS3", "AC:9B:0A": "PS3",
    # Sony PS4
    "00:15:C1": "PS4", "00:E4:21": "PS4", "0C:70:43": "PS4",
    "50:B0:3B": "PS4", "5C:96:66": "PS4", "60:5B:B4": "PS4",
    "68:28:6C": "PS4", "84:E6:57": "PS4", "A8:E3:EE": "PS4",
    "AC:89:95": "PS4", "D4:F7:D5": "PS4", "40:49:0F": "PS4",
    # Sony PS5
    "1C:98:C1": "PS5", "5C:84:3C": "PS5", "80:60:B7": "PS5",
    "9C:37:CB": "PS5", "B4:0A:D8": "PS5", "E8:6E:3A": "PS5",
    "EC:74:8C": "PS5",
    # Sony PSP
    "00:25:E7": "PSP", "00:90:D9": "PSP", "00:1C:B8": "PSP",
    # Sony PS Vita
    "00:00:00": "PS Vita",  # placeholder — Vita uses random MACs
    # Microsoft Xbox (original)
    "00:50:F2": "Xbox", "08:D4:0C": "Xbox",
    # Microsoft Xbox 360
    "00:22:48": "Xbox 360", "30:59:B7": "Xbox 360",
    "58:82:A8": "Xbox 360", "7C:1E:52": "Xbox 360",
    # Microsoft Xbox One / Series
    "28:18:78": "Xbox One", "60:45:CB": "Xbox One",
    "98:5F:D3": "Xbox One", "C8:3D:D4": "Xbox One",
    "20:7B:D2": "Xbox One",
    # Nintendo GameCube / Wii
    "00:09:BF": "GameCube",
    # Valve Steam Deck
    "A4:AE:11": "Steam Deck",
}

# Platform ID mapping from console type
CONSOLE_PLATFORM = {
    "Nintendo Switch": "switch",
    "PS2":  "ps2",
    "PS3":  "ps3",
    "PS4":  "ps3",   # PS4 uses PS3 relay protocol
    "PS5":  "ps3",   # PS5 uses PS3 relay protocol
    "PSP":  "psp",
    "PS Vita": "vita",
    "Xbox": "xbox",
    "Xbox 360": "xbox360",
    "Xbox One": "xboxone",
    "GameCube": "gamecube",
    "Wii": "wii",
    "Steam Deck": "pc",
}


@dataclass
class DetectedDevice:
    mac: str
    ip: str
    manufacturer: str = "Unknown"
    console_type: str = "Unknown"
    platform: str = ""
    hostname: str = ""
    custom_name: str = ""
    nm_user: str = ""
    is_emulator: bool = False
    emulator_name: str = ""


def get_oui(mac: str) -> str:
    parts = mac.upper().replace("-", ":").split(":")
    if len(parts) < 3:
        return ""
    return ":".join(parts[:3])


def identify_device(mac: str) -> tuple:
    oui = get_oui(mac)
    console_type = OUI_MAP.get(oui, "Unknown")
    if console_type == "Unknown":
        return "Unknown", "Unknown", ""
    plat = CONSOLE_PLATFORM.get(console_type, "")
    # Manufacturer from console type
    if console_type.startswith("PS") or console_type in ("PSP", "PS Vita"):
        mfr = "Sony"
    elif console_type in ("Nintendo Switch", "GameCube", "Wii"):
        mfr = "Nintendo"
    elif "Xbox" in console_type:
        mfr = "Microsoft"
    else:
        mfr = "Unknown"
    return mfr, console_type, plat


def get_arp_table() -> list:
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
            # Filter invalid IPs
            if (ip.startswith("224.") or ip.startswith("239.") or
                ip.startswith("255.") or ip.startswith("172.") or
                ip.endswith(".255") or mac == "FF:FF:FF:FF:FF:FF"):
                continue
            mfr, console_type, plat = identify_device(mac)
            devices.append({
                "ip": ip,
                "mac": mac,
                "manufacturer": mfr,
                "console_type": console_type,
                "platform": plat
            })
    except Exception as e:
        print(f"[Network] ARP scan error: {e}")
    return devices


def _ping_one(ip: str):
    try:
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        if platform.system() == "Windows":
            subprocess.run(["ping", "-n", "2", "-w", "500", ip],
                           capture_output=True, timeout=2, creationflags=flags)
        else:
            subprocess.run(["ping", "-c", "2", "-W", "1", ip],
                           capture_output=True, timeout=2)
    except Exception:
        pass


def ping_subnet(base_ip: str, count: int = 254):
    """Parallel ping of subnet using ThreadPoolExecutor for speed."""
    parts = base_ip.split(".")
    if len(parts) < 3:
        return
    subnet = ".".join(parts[:3])
    ips = [f"{subnet}.{i}" for i in range(1, count + 1)]
    with ThreadPoolExecutor(max_workers=64) as executor:
        executor.map(_ping_one, ips)


def get_local_ip() -> str:
    import ipaddress
    try:
        for iface_ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if iface_ip.startswith("192.168."):
                return iface_ip
            ip = ipaddress.ip_address(iface_ip)
            if not ip.is_loopback and not iface_ip.startswith("100.") and not iface_ip.startswith("172."):
                pass
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip.startswith("192.168."):
            return ip
    except Exception:
        pass
    return "192.168.1.1"


def scan_network(callback=None) -> list:
    local_ip = get_local_ip()
    print(f"[Network] Local IP: {local_ip}, scanning subnet...")
    # Pre-ping known console IPs from ARP cache first
    import subprocess as _sp
    try:
        if platform.system() == "Windows":
            arp_out = _sp.check_output("arp -a", shell=True).decode("utf-8", errors="ignore")
        else:
            arp_out = _sp.check_output(["arp", "-a"], stderr=_sp.DEVNULL).decode("utf-8", errors="ignore")
        import re as _re
        known_ips = _re.findall(r"(\d+\.\d+\.\d+\.\d+)", arp_out)
        with ThreadPoolExecutor(max_workers=32) as ex:
            ex.map(_ping_one, known_ips[:50])
    except Exception:
        pass
    ping_subnet(local_ip)
    raw = get_arp_table()
    devices = []
    for d in raw:
        device = DetectedDevice(
            mac=d["mac"],
            ip=d["ip"],
            manufacturer=d["manufacturer"],
            console_type=d["console_type"],
            platform=d.get("platform", "")
        )
        try:
            device.hostname = socket.gethostbyaddr(d["ip"])[0]
        except Exception:
            pass
        devices.append(device)
        if callback:
            callback(device)
    consoles = sum(1 for d in devices if d.console_type != "Unknown")
    print(f"[Network] Found {len(devices)} devices ({consoles} consoles)")
    return devices


EMULATOR_PROCESSES = {
    "dolphin.exe":     ("Dolphin",  "gamecube"),
    "dolphin-emu":     ("Dolphin",  "gamecube"),
    "pcsx2.exe":       ("PCSX2",    "ps2"),
    "pcsx2-qt.exe":    ("PCSX2",    "ps2"),
    "rpcs3.exe":       ("RPCS3",    "ps3"),
    "xemu.exe":        ("Xemu",     "xbox"),
    "xenia.exe":       ("Xenia",    "xbox360"),
    "xenia_canary.exe":("Xenia",    "xbox360"),
    "ryujinx.exe":     ("Ryujinx",  "switch"),
    "ryujinx":         ("Ryujinx",  "switch"),
    "ppsspp.exe":      ("PPSSPP",   "psp"),
    "ppsspp":          ("PPSSPP",   "psp"),
    "vita3k.exe":      ("Vita3k",   "vita"),
    "vita3k":          ("Vita3k",   "vita"),
    "pcsx2":           ("PCSX2",    "ps2"),
    "rpcs3":           ("RPCS3",    "ps3"),
}


def detect_emulators() -> list:
    found = []
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("tasklist /fo csv /nh", shell=True).decode("utf-8", errors="ignore")
            running = [line.split(",")[0].strip('"').lower() for line in output.splitlines()]
        else:
            output = subprocess.check_output(["ps", "-e", "-o", "comm="],
                stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
            running = [line.strip().lower() for line in output.splitlines()]

        for proc, (name, platform_id) in EMULATOR_PROCESSES.items():
            if proc.lower() in running:
                found.append({
                    "ip": "EMU",
                    "mac": "00:00:00:00:00:00",
                    "manufacturer": name,
                    "console_type": name,
                    "platform": platform_id,
                    "is_emulator": True
                })
    except Exception as e:
        print(f"[Network] Emulator detection error: {e}")
    return found