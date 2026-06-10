# Nintendo Switch — NM-Play Setup

## Option 1 — CFW (Recommended, no PC needed)

Use the **ldn_mitm sysmodule** from [NM_ldn_mitm_relay](https://github.com/Necrosiak/NM_ldn_mitm_relay).
The Switch connects directly to the NetworkMemories relay — no PC required.

### Requirements
- Atmosphere CFW (1.11.1+)
- ldn_mitm already installed

### Setup
1. Download `exefs.nsp` from NM_ldn_mitm_relay releases
2. Copy to `atmosphere/contents/4200000000000010/exefs.nsp`
3. The relay is pre-configured to `networkmemories.com`
4. Enable ldn_mitm via **ldnmitm_config** overlay (Y + X LOGIN)
5. Launch any game in LAN mode

---

## Option 2 — Stock Switch or CFW without ldn_mitm

Use **NM-Play desktop client**.

### Switch IP Configuration
- Settings → Internet → Your network → Change Settings → Manual IP
- IP: `10.13.1.X` (unique per player, range 10.13.0.1–10.13.255.254)
- Subnet Mask: `255.255.0.0`
- Gateway: `10.13.37.1`

### LAN Mode activation
Hold **L + R + Left Stick** in game to activate LAN mode.

### Compatible games (25 known)
Mario Kart 8 Deluxe, Splatoon 2/3, Super Smash Bros. Ultimate, Pokémon Sword/Shield, and more.
