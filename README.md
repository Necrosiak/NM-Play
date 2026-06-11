# NM-Play Overlay

> **Tesla overlay for Nintendo Switch CFW**
> Shows NM-Play lobbies and online players directly on your Switch — no PC needed.
> Part of the [NetworkMemories](https://network-memories.com) project.

---

> *"Reviving the past, connecting the present."* — NetworkMemories

---

## What is this?

A Tesla overlay that connects to the NM-Play relay API and displays:
- Active lobbies per platform in real time
- Players online count
- Server status

Open with the Tesla menu combo (L + R + DPad-Down).

## Requirements

- Atmosphere CFW (1.11.1+)
- Tesla menu (nx-ovlloader + Tesla-Menu)
- Internet connection on Switch

## Installation

1. Download `ovl-nm-play.ovl` from [Releases](https://github.com/Necrosiak/NM-Play-Overlay/releases)
   or copy from `sd_card/switch/.overlays/ovl-nm-play.ovl`
2. Copy to `sd:/switch/.overlays/ovl-nm-play.ovl`
3. Open Tesla menu and select NM-Play

## Controls

| Button | Action |
|--------|--------|
| R | Refresh lobbies |
| B | Close overlay |

## Build from source

```bash
# Install dependencies
dkp-pacman -S switch-curl switch-mbedtls

# Clone libtesla
git clone https://github.com/ITotalJustice/libtesla lib/libtesla

# Build (Docker recommended)
docker run --rm -v "$(pwd):/project" devkitpro/devkita64:20230526 bash -c \
  "cd /project && make NM_API_HOST=your-server.com NM_API_PORT=18090"

# Convert to overlay
elf2nro ovl-nm-play.elf ovl-nm-play.ovl
```

## Self-hosting

By default this overlay points to `localhost`. To use your own NM-Play server:

```bash
make NM_API_HOST=your-server.com NM_API_PORT=18090
```

## Credits

| Who | What |
|-----|------|
| **NerdHz** | NetworkMemories — Founder, vision & community |
| **Nekyron** | NetworkMemories — Co-founder, infrastructure & development |
| [WerWolv](https://github.com/WerWolv) | libtesla & Tesla menu |
| [ITotalJustice](https://github.com/ITotalJustice) | libtesla fork (libnx modern compat) |

## License

GPLv2