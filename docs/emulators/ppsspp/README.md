# PPSSPP (PlayStation Portable) — NM-Play Setup

## Requirements
- PPSSPP (latest stable, 1.17+)
- NM-Play desktop client

## Setup
1. In PPSSPP: Settings → Networking
   - Enable networking: ON
   - Pro Adhoc Server IP: `networkmemories.com`
   - Port: `27312`
   - Port Offset: `10000` (must match all players)
2. Launch NM-Play, select PSP, click Connect
3. Launch a game with Ad-Hoc multiplayer

## Notes
- PPSSPP and real PSP (with Kethen/aemu plugin) can play together
- aemu_postoffice relay mode available in PPSSPP 1.20+
- For postoffice relay: set postoffice server to `networkmemories.com:27313`
