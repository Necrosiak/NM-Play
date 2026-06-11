# NM-Play

> **Universal LAN Play Launcher — NetworkMemories**
> Like XLink Kai, but 100% hosted by NetworkMemories.
> Part of the [NetworkMemories](https://network-memories.com) project.

---

> *"Reviving the past, connecting the present."* — [NetworkMemories](https://network-memories.com)

---

## What is NM-Play?

NM-Play is a free, open-source LAN tunneling launcher.

- Login with your **NetworkMemories account**
- See **active lobbies** for every supported platform in real time
- **One click** to connect and play
- Works with **original consoles** AND **emulators** in the same lobby
- **EU relay server** hosted by NetworkMemories
- No third party — 100% NetworkMemories infrastructure

## Supported Platforms

| Console | Physical | Emulator | Method |
|---------|----------|----------|--------|
| Nintendo Switch | ✅ CFW | ✅ Ryujinx/Citron | ldn_mitm sysmodule (no PC needed) |
| Nintendo Switch | ✅ stock (LAN games) | ✅ | NM-Play client |
| PlayStation 2 | ✅ | ✅ PCSX2 | L2 tunnel |
| PlayStation 3 | ✅ | ✅ RPCS3 | L2 tunnel |
| PlayStation Portable | ✅ CFW | ✅ PPSSPP | aemu adhoc |
| PlayStation Vita | ✅ CFW | ✅ Vita3k | aemu adhoc |
| Xbox (original) | ✅ | ✅ Xemu | L2 tunnel |
| Xbox 360 | ✅ | ✅ Xenia | L2 tunnel |
| GameCube | ✅ BBA | ✅ Dolphin | L2 tunnel |
| Wii | ✅ homebrew | ✅ Dolphin | L2 tunnel |
| PC LAN | ✅ | ✅ | L2 tunnel |

## Downloads

| Platform | Download | Status |
|----------|----------|--------|
| Windows | [NM-Play-Windows.exe](https://github.com/Necrosiak/NM-Play/releases/latest) | ✅ v0.1.0-beta |
| Android | [NM-Play-Android.apk](https://github.com/Necrosiak/NM-Play/releases/latest) | ✅ v0.1.0-beta |
| Linux | Coming soon | 🔄 |
| macOS | Coming soon | 🔄 |
| Switch CFW | [NM_ldn_mitm_relay](https://github.com/Necrosiak/NM_ldn_mitm_relay/releases/latest) | ✅ no PC needed |
| Switch Overlay | [NM-Play-Overlay](https://github.com/Necrosiak/NM-Play-Overlay/releases/latest) | ✅ v0.1.0-beta |
| NM-Bridge | Raspberry Pi gateway | 🔄 In development |
| NM-Link | ESP32-S3 PCB gateway | 🔄 In development |

## Server

NM-Play relay is **self-hosted by NetworkMemories**:
- Host: `network-memories.com`
- No account sharing with any third party
- Full control over data and uptime

## Quick Start

1. Download NM-Play for your OS
2. Login with your NetworkMemories account at [network-memories.com](https://network-memories.com)
3. Select your console/emulator
4. Browse lobbies and join or create a game
5. NM-Play configures everything automatically

## Setup Guides

### Consoles
- [Nintendo Switch](docs/consoles/switch/README.md)
- [PlayStation 2](docs/consoles/ps2/README.md)
- [PlayStation 3](docs/consoles/ps3/README.md)
- [PlayStation Portable](docs/consoles/psp/README.md)
- [PlayStation Vita](docs/consoles/vita/README.md)
- [Xbox original](docs/consoles/xbox/README.md)
- [Xbox 360](docs/consoles/xbox360/README.md)
- [GameCube](docs/consoles/gamecube/README.md)
- [Wii](docs/consoles/wii/README.md)

### Emulators
- [Dolphin — GameCube/Wii](docs/emulators/dolphin/README.md)
- [PCSX2 — PS2](docs/emulators/pcsx2/README.md)
- [RPCS3 — PS3](docs/emulators/rpcs3/README.md)
- [Xemu — Xbox](docs/emulators/xemu/README.md)
- [Xenia — Xbox 360](docs/emulators/xenia/README.md)
- [Ryujinx — Switch](docs/emulators/ryujinx/README.md)
- [PPSSPP — PSP](docs/emulators/ppsspp/README.md)
- [Vita3k — PS Vita](docs/emulators/vita3k/README.md)

## Architecture
Console/Emulator
↓ LAN packets (broadcast)
NM-Play Client (PC/Android)
↓ L2 tunnel / SLP / aemu
NetworkMemories Relay Server (EU)
↓ relay + lobby API + NM auth
↓
NM-Play Client UI (lobbies, chat)
Switch Tesla Overlay (no PC needed)
network-memories.com/nmplay


## Components

| Component | Description | Status |
|-----------|-------------|--------|
| `server/` | Relay server + lobby API (self-hosted) | ✅ Live |
| `client/` | Desktop launcher GUI (Win/Linux/macOS) | ✅ v0.1.0-beta |
| `android/` | Android app (Flutter) | ✅ v0.1.0-beta |
| `switch-plugin/` | Tesla overlay (Switch CFW) | ✅ v0.1.0-beta |
| `docs/` | Setup guides for all consoles & emulators | ✅ |

## Disclaimer

NM-Play is a LAN tunneling service only.
**We do not provide any games, ROMs or illegal copies.**
You must legally own the games you play. Piracy is not tolerated on NetworkMemories.

## Credits

| Who | What |
|-----|------|
| **NerdHz** | NetworkMemories — Founder, vision & community |
| **Nekyron** | NetworkMemories — Co-founder, infrastructure & development |
| [mborgerson/l2tunnel](https://github.com/mborgerson/l2tunnel) | L2 tunneling core |
| [spacemeowx2/switch-lan-play](https://github.com/spacemeowx2/switch-lan-play) | Switch SLP protocol |
| [Kethen/aemu](https://github.com/Kethen/aemu) | PSP/Vita adhoc relay |

---
> *"Reviving the past, connecting the present."* — [NetworkMemories](https://network-memories.com)

## License

GPL-3.0