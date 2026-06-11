#!/usr/bin/env python3
"""
NM-Play — Universal LAN Play Launcher
NetworkMemories — network-memories.com
"Reviving the past, connecting the present." — NerdHz & Nekyron
"""

import sys, os, threading, json, time, platform
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.api    import NMPlayAPI
from core.auth   import NMAuth
from core.relay  import RelayManager
from core.network import scan_network, detect_emulators
from core.config import APP_NAME, APP_VERSION, API_BASE, AUTH_URL

# ── Theme ────────────────────────────────────────────────────────────────────
BG       = "#0f0f1a"
BG_CARD  = "#1a1a2e"
BG_ITEM  = "#0d1b2a"
BG_SEL   = "#16213e"
ACCENT   = "#e94560"
TEXT     = "#eaeaea"
TEXT_DIM = "#8888aa"
GREEN    = "#00c896"
RED      = "#e94560"
FONT     = "Segoe UI"

# (id, label, color, icon, manufacturer)
PLATFORMS = [
    ("ps2",      "PS2",         "#00439c", "🔵", "Sony"),
    ("ps3",      "PS3",         "#003087", "🔵", "Sony"),
    ("psp",      "PSP",         "#1a1a8c", "🟣", "Sony"),
    ("vita",     "PS Vita",     "#003791", "🔵", "Sony"),
    ("switch",   "Switch",      "#e4000f", "🔴", "Nintendo"),
    ("switch2",  "Switch 2",    "#cc0000", "🔴", "Nintendo"),
    ("gamecube", "GameCube",    "#6a0dad", "🟣", "Nintendo"),
    ("wii",      "Wii",         "#c0c0c0", "⚪", "Nintendo"),
    ("xbox",     "Xbox",        "#107c10", "🟢", "Microsoft"),
    ("xboxone",  "Xbox One",    "#107c10", "🟢", "Microsoft"),
    ("xbox360",  "Xbox 360",    "#52b043", "🟢", "Microsoft"),
    ("pc",       "PC LAN",      "#00b4d8", "🔵", "PC"),
]
PLATFORM_MAP = {p[0]: p for p in PLATFORMS}

# Grouped by manufacturer
PLATFORM_GROUPS = [
    ("Sony",      ["ps2","ps3","psp","vita"],             "#00439c"),
    ("Nintendo",  ["switch","switch2","gamecube","wii"],  "#e4000f"),
    ("Microsoft", ["xbox","xboxone","xbox360"],           "#107c10"),
    ("PC",        ["pc"],                                 "#00b4d8"),
]

# ── Main App ─────────────────────────────────────────────────────────────────
class NMPlay(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1000x680")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.auth     = NMAuth()
        self.api      = NMPlayAPI()
        self.relay    = RelayManager(log_callback=self._log)
        self.platform = "switch"
        self.lobbies  = []
        self.devices  = []
        self.current_lobby = None
        self.show_logs = False
        self._heartbeat_thread = None

        self._build_ui()
        self._check_server()

        if self.auth.is_logged_in():
            self._update_user_display()
            self._connect_to_server()
        else:
            self.after(800, self._show_login)

        self._start_refresh()

    # ── UI Build ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_platform_bar()
        self._build_main()
        self._build_statusbar()

    def _build_header(self):
        h = tk.Frame(self, bg=BG_CARD, pady=10)
        h.pack(fill="x")

        # Logo
        logo = tk.Frame(h, bg=BG_CARD)
        logo.pack(side="left", padx=16)
        tk.Label(logo, text="NM", font=(FONT, 22, "bold"), bg=BG_CARD, fg=ACCENT).pack(side="left")
        tk.Label(logo, text="-Play", font=(FONT, 22, "bold"), bg=BG_CARD, fg=TEXT).pack(side="left")
        tk.Label(logo, text=f"  v{APP_VERSION}", font=(FONT, 9), bg=BG_CARD, fg=TEXT_DIM).pack(side="left", pady=6)

        # Right controls
        right = tk.Frame(h, bg=BG_CARD)
        right.pack(side="right", padx=16)

        self.lbl_server = tk.Label(right, text="●  ...", font=(FONT, 9), bg=BG_CARD, fg=TEXT_DIM)
        self.lbl_server.pack(side="right", padx=12)

        self.btn_user = tk.Button(right, text="Connexion",
            font=(FONT, 9, "bold"), bg=ACCENT, fg="white",
            relief="flat", padx=12, pady=5, cursor="hand2",
            command=self._show_login)
        self.btn_user.pack(side="right", padx=4)

    def _build_platform_bar(self):
        bar = tk.Frame(self, bg=BG_SEL, pady=4)
        bar.pack(fill="x")
        # Second row for sub-platforms
        self._sub_bar = tk.Frame(self, bg=BG_SEL, pady=2)
        self._sub_bar.pack(fill="x")
        self._sub_bar.pack_forget()  # Hidden initially

        self.platform_btns = {}
        self._group_expanded = {}

        for gname, gids, gcolor in PLATFORM_GROUPS:
            # Group button
            grp_frame = tk.Frame(bar, bg=BG_SEL)
            grp_frame.pack(side="left", padx=1)

            self._group_expanded[gname] = False

            # Sub-platform buttons (hidden by default)
            sub_frame = tk.Frame(self._sub_bar, bg=BG_SEL)

            def make_toggle(gn, sf, gc, gids_=gids):
                def toggle():
                    self._group_expanded[gn] = not self._group_expanded[gn]
                    if self._group_expanded[gn]:
                        sf.pack(side="left")
                        self._sub_bar.pack(fill="x")
                        # Auto-select first platform of group
                        self._select_platform(gids_[0])
                    else:
                        sf.pack_forget()
                        # Hide sub_bar if no group expanded
                        if not any(self._group_expanded.values()):
                            self._sub_bar.pack_forget()
                return toggle

            grp_btn = tk.Button(grp_frame,
                text=f"{gname} ▾",
                font=(FONT, 8, "bold"),
                bg=BG_SEL, fg=gcolor,
                relief="flat", padx=10, pady=4,
                cursor="hand2",
                command=make_toggle(gname, sub_frame, gcolor))
            grp_btn.pack(side="left")

            # Platform buttons inside group
            for pid in gids:
                pinfo = PLATFORM_MAP.get(pid)
                if not pinfo:
                    continue
                _, pname, color, icon, _ = pinfo
                btn = tk.Button(sub_frame,
                    text=f"{icon} {pname}",
                    font=(FONT, 8), bg=BG_SEL, fg=TEXT_DIM,
                    relief="flat", padx=6, pady=4,
                    cursor="hand2",
                    command=lambda p=pid: self._select_platform(p))
                btn.pack(side="left", padx=1)
                self.platform_btns[pid] = (btn, color)

        # Expand Sony by default
        self._select_platform("ps2")
        # Auto-expand Sony group
        for gname, gids, gcolor in PLATFORM_GROUPS:
            if gname == "Sony":
                self._group_expanded[gname] = True

    def _build_main(self):
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=8, pady=4)

        # ── Left: lobbies ────────────────────────────────────────────
        left = tk.Frame(main, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        # Lobby toolbar
        toolbar = tk.Frame(left, bg=BG)
        toolbar.pack(fill="x", pady=(4, 2))

        tk.Label(toolbar, text="Lobbies actifs",
            font=(FONT, 10, "bold"), bg=BG, fg=TEXT).pack(side="left")

        self.lbl_online = tk.Label(toolbar, text="0 en ligne",
            font=(FONT, 8), bg=BG, fg=TEXT_DIM)
        self.lbl_online.pack(side="left", padx=8)

        btn_frame = tk.Frame(toolbar, bg=BG)
        btn_frame.pack(side="right")

        tk.Button(btn_frame, text="⟳ Rafraîchir",
            font=(FONT, 8), bg=BG_CARD, fg=TEXT_DIM,
            relief="flat", padx=8, pady=3, cursor="hand2",
            command=self._refresh_lobbies).pack(side="right", padx=2)

        tk.Button(btn_frame, text="+ Créer",
            font=(FONT, 8, "bold"), bg=ACCENT, fg="white",
            relief="flat", padx=10, pady=3, cursor="hand2",
            command=self._create_lobby).pack(side="right", padx=2)

        # Lobby list
        self.lobby_frame = tk.Frame(left, bg=BG)
        self.lobby_frame.pack(fill="both", expand=True)

        # Current lobby panel
        self.lobby_panel = tk.Frame(left, bg=BG_CARD,
            relief="flat", pady=8, padx=10)
        self.lobby_panel.pack(fill="x", pady=4)
        self.lobby_panel.pack_forget()

        # ── Right: devices + relay ───────────────────────────────────
        right = tk.Frame(main, bg=BG_CARD, width=240)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)

        tk.Label(right, text="Appareils détectés",
            font=(FONT, 9, "bold"), bg=BG_CARD, fg=TEXT,
            pady=8).pack()

        # Scrollable device list
        dev_scroll_frame = tk.Frame(right, bg=BG_CARD)
        dev_scroll_frame.pack(fill="both", expand=True, padx=4)
        dev_canvas = tk.Canvas(dev_scroll_frame, bg=BG_CARD, highlightthickness=0, height=150)
        dev_scroll = tk.Scrollbar(dev_scroll_frame, orient="vertical", command=dev_canvas.yview)
        dev_canvas.configure(yscrollcommand=dev_scroll.set)
        dev_scroll.pack(side="right", fill="y")
        dev_canvas.pack(side="left", fill="both", expand=True)
        self.device_list = tk.Frame(dev_canvas, bg=BG_CARD)
        dev_canvas.create_window((0,0), window=self.device_list, anchor="nw")
        self.device_list.bind("<Configure>",
            lambda e: dev_canvas.configure(scrollregion=dev_canvas.bbox("all")))

        # Manual console add
        tk.Label(right, text="Ajouter manuellement",
            font=(FONT, 8), bg=BG_CARD, fg=TEXT_DIM).pack(pady=(8,2))

        manual_frame = tk.Frame(right, bg=BG_CARD)
        manual_frame.pack(fill="x", padx=4)

        self.entry_manual_ip = tk.Entry(manual_frame,
            font=(FONT, 8), bg=BG_ITEM, fg=TEXT,
            insertbackground=TEXT, relief="flat", width=14)
        self.entry_manual_ip.insert(0, "IP de la console")
        self.entry_manual_ip.pack(side="left", padx=(0,2), ipady=4)

        # Platform dropdown for manual
        self.manual_platform = tk.StringVar(value="ps2")
        platforms_list = [p[0] for p in PLATFORMS]
        self.combo_platform = ttk.Combobox(manual_frame,
            textvariable=self.manual_platform,
            values=platforms_list, width=8,
            state="readonly")
        self.combo_platform.pack(side="left")

        tk.Button(right, text="+ Ajouter",
            font=(FONT, 8), bg=BG_CARD, fg=TEXT_DIM,
            relief="flat", padx=8, pady=3, cursor="hand2",
            command=self._add_manual_device).pack(pady=4)

        # Relay button
        self.btn_relay = tk.Button(right, text="Connecter au relay",
            font=(FONT, 9, "bold"), bg=ACCENT, fg="white",
            relief="flat", padx=10, pady=6, cursor="hand2",
            command=self._toggle_relay)
        self.btn_relay.pack(fill="x", padx=8, pady=8)

        self.lbl_relay = tk.Label(right, text="Non connecté",
            font=(FONT, 8), bg=BG_CARD, fg=TEXT_DIM)
        self.lbl_relay.pack()

        # Logs toggle
        tk.Button(right, text="📋 Logs",
            font=(FONT, 8), bg=BG_SEL, fg=TEXT_DIM,
            relief="flat", padx=8, pady=3, cursor="hand2",
            command=self._toggle_logs).pack(fill="x", padx=8, pady=(16,2))

        # Log area (hidden by default)
        self.log_frame = tk.Frame(right, bg=BG_CARD)
        self.log_text = tk.Text(self.log_frame,
            font=("Consolas", 7), bg=BG_ITEM, fg=TEXT_DIM,
            relief="flat", height=8, state="disabled",
            wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=BG_SEL, pady=3)
        bar.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(bar, text="NM-Play — network-memories.com",
            font=(FONT, 8), bg=BG_SEL, fg=TEXT_DIM)
        self.lbl_status.pack(side="left", padx=10)

        tk.Label(bar,
            text='"Reviving the past, connecting the present." — NerdHz & Nekyron',
            font=(FONT, 7, "italic"), bg=BG_SEL, fg=TEXT_DIM).pack(side="right", padx=10)

    # ── Platform ─────────────────────────────────────────────────────────────

    def _select_platform(self, pid):
        self.platform = pid
        for p, (btn, color) in self.platform_btns.items():
            if p == pid:
                btn.configure(bg=color, fg="white")
            else:
                btn.configure(bg=BG_SEL, fg=TEXT_DIM)
        self._refresh_lobbies()

    # ── Lobbies ──────────────────────────────────────────────────────────────

    def _refresh_lobbies(self):
        def _do():
            try:
                lobbies = self.api.get_lobbies(self.platform)
                self.lobbies = lobbies if lobbies else []
                self.after(0, self._render_lobbies)
            except Exception as e:
                self._log(f"[API] {e}")
        threading.Thread(target=_do, daemon=True).start()

    def _render_lobbies(self):
        for w in self.lobby_frame.winfo_children():
            w.destroy()

        if not self.lobbies:
            tk.Label(self.lobby_frame,
                text=f"Aucun lobby {self.platform.upper()} actif\nSoyez le premier !",
                font=(FONT, 9), bg=BG, fg=TEXT_DIM,
                pady=30, justify="center").pack()
            self.lbl_online.configure(text="0 en ligne")
            return

        total = sum(len(l.get("players", [])) for l in self.lobbies)
        self.lbl_online.configure(text=f"{total} joueur(s) en ligne")

        for lobby in self.lobbies:
            self._render_lobby_card(lobby)

    def _render_lobby_card(self, lobby):
        pid     = lobby.get("platform", "")
        pinfo   = PLATFORM_MAP.get(pid, ("", pid, ACCENT, ""))
        color   = pinfo[2]
        players = lobby.get("players", [])
        max_p   = lobby.get("maxPlayers", 8)
        is_priv = lobby.get("private", False)
        is_full = len(players) >= max_p

        card = tk.Frame(self.lobby_frame, bg=BG_ITEM, pady=6, padx=8, cursor="hand2")
        card.pack(fill="x", padx=4, pady=2)

        tk.Frame(card, bg=color, width=4).pack(side="left", fill="y", padx=(0,8))

        info = tk.Frame(card, bg=BG_ITEM)
        info.pack(side="left", fill="both", expand=True)

        # Name row
        name_row = tk.Frame(info, bg=BG_ITEM)
        name_row.pack(fill="x")
        tk.Label(name_row,
            text=("🔒 " if is_priv else "") + lobby.get("name", "Lobby"),
            font=(FONT, 9, "bold"), bg=BG_ITEM, fg=TEXT).pack(side="left")
        tk.Label(name_row, text=f"  {pid.upper()}",
            font=(FONT, 7), bg=BG_ITEM, fg=color).pack(side="left")

        # Game + players row
        game_row = tk.Frame(info, bg=BG_ITEM)
        game_row.pack(fill="x")
        tk.Label(game_row, text=lobby.get("game", ""),
            font=(FONT, 8), bg=BG_ITEM, fg=TEXT_DIM).pack(side="left")

        # Players avatars
        for p in players[:8]:
            uname = p.get("username", "?")[:2].upper()
            lbl = tk.Label(game_row, text=uname,
                font=(FONT, 7, "bold"),
                bg=color, fg="white",
                padx=3, pady=1, relief="flat")
            lbl.pack(side="left", padx=1)

        # Count
        count_color = RED if is_full else GREEN
        tk.Label(card, text=f"{len(players)}/{max_p}",
            font=(FONT, 10, "bold"), bg=BG_ITEM, fg=count_color).pack(side="right")

        # Click to join
        card.bind("<Double-Button-1>",
            lambda e, lid=lobby.get("id"), priv=is_priv: self._join_lobby(lid, priv))
        for w in card.winfo_children():
            w.bind("<Double-Button-1>",
                lambda e, lid=lobby.get("id"), priv=is_priv: self._join_lobby(lid, priv))

    def _create_lobby(self):
        if not self.auth.is_logged_in():
            messagebox.showwarning("Connexion requise", "Connecte-toi pour créer un lobby.")
            self._show_login()
            return

        # Create lobby dialog
        dialog = tk.Toplevel(self)
        dialog.title("Créer un lobby")
        dialog.geometry("340x320")
        dialog.configure(bg=BG_CARD)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Créer un lobby",
            font=(FONT, 12, "bold"), bg=BG_CARD, fg=TEXT, pady=12).pack()

        def field(label, default=""):
            f = tk.Frame(dialog, bg=BG_CARD)
            f.pack(fill="x", padx=20, pady=4)
            tk.Label(f, text=label, font=(FONT, 8), bg=BG_CARD, fg=TEXT_DIM, width=12, anchor="w").pack(side="left")
            e = tk.Entry(f, font=(FONT, 9), bg=BG_ITEM, fg=TEXT, insertbackground=TEXT, relief="flat")
            e.insert(0, default)
            e.pack(side="left", fill="x", expand=True, ipady=4, padx=(4,0))
            return e

        e_name  = field("Nom du lobby", f"Lobby de {self.auth.username or 'joueur'}")
        e_game  = field("Jeu")
        e_pass  = field("Mot de passe", "")

        # Platform selector
        pf = tk.Frame(dialog, bg=BG_CARD)
        pf.pack(fill="x", padx=20, pady=4)
        tk.Label(pf, text="Plateforme", font=(FONT, 8), bg=BG_CARD, fg=TEXT_DIM, width=12, anchor="w").pack(side="left")
        plat_var = tk.StringVar(value=self.platform)
        combo = ttk.Combobox(pf, textvariable=plat_var,
            values=[p[0] for p in PLATFORMS], state="readonly", width=16)
        combo.pack(side="left", padx=(4,0))

        # Max players
        mf = tk.Frame(dialog, bg=BG_CARD)
        mf.pack(fill="x", padx=20, pady=4)
        tk.Label(mf, text="Max joueurs", font=(FONT, 8), bg=BG_CARD, fg=TEXT_DIM, width=12, anchor="w").pack(side="left")
        max_var = tk.StringVar(value="8")
        tk.Spinbox(mf, from_=2, to=16, textvariable=max_var,
            font=(FONT, 9), bg=BG_ITEM, fg=TEXT, width=4,
            relief="flat").pack(side="left", padx=(4,0))

        def _do_create():
            name = e_name.get().strip()
            game = e_game.get().strip()
            pw   = e_pass.get().strip()
            plat = plat_var.get()
            maxp = int(max_var.get() or 8)

            if not name:
                messagebox.showerror("Erreur", "Le nom est requis.", parent=dialog)
                return

            dialog.destroy()

            def _create():
                result = self.api.create_lobby(
                    name=name, platform=plat, game=game,
                    password=pw, max_players=maxp,
                    token=self.auth.token,
                    username=self.auth.username or "Joueur"
                )
                if result and result.get("ok"):
                    self.current_lobby = result.get("lobby")
                    self._log(f"Lobby créé : {name}")
                    self.after(0, self._show_current_lobby)
                    self.after(0, self._refresh_lobbies)
                    if not self.relay.running:
                        self.after(0, self._toggle_relay)
                else:
                    self._log(f"Erreur création lobby: {result}")
            threading.Thread(target=_create, daemon=True).start()

        tk.Button(dialog, text="Créer le lobby",
            font=(FONT, 10, "bold"), bg=ACCENT, fg="white",
            relief="flat", padx=16, pady=8, cursor="hand2",
            command=_do_create).pack(pady=16)

    def _join_lobby(self, lobby_id, is_private=False):
        if not self.auth.is_logged_in():
            messagebox.showwarning("Connexion requise", "Connecte-toi pour rejoindre un lobby.")
            self._show_login()
            return

        password = ""
        if is_private:
            password = simpledialog.askstring("Lobby privé", "Mot de passe :", show="*") or ""
            if not password:
                return

        def _do():
            result = self.api.join_lobby(lobby_id, password, self.auth.token, username=self.auth.username or "Joueur")
            if result and result.get("ok"):
                # Find lobby in list
                for l in self.lobbies:
                    if l.get("id") == lobby_id:
                        self.current_lobby = l
                        break
                self._log(f"Lobby rejoint !")
                self.after(0, self._show_current_lobby)
                self.after(0, self._refresh_lobbies)
                if not self.relay.running:
                    self.after(0, self._toggle_relay)
            else:
                err = result.get("error", "Erreur") if result else "Serveur inaccessible"
                self._log(f"Erreur : {err}")
                self.after(0, lambda: messagebox.showerror("Erreur", err))
        threading.Thread(target=_do, daemon=True).start()

    def _leave_lobby(self):
        def _do():
            self.api.leave_lobby(self.auth.token)
            self.current_lobby = None
            self._log("Lobby quitté")
            self.after(0, self._hide_current_lobby)
            self.after(0, self._refresh_lobbies)
        threading.Thread(target=_do, daemon=True).start()

    def _show_current_lobby(self):
        if not self.current_lobby:
            return
        for w in self.lobby_panel.winfo_children():
            w.destroy()

        l = self.current_lobby
        color = PLATFORM_MAP.get(l.get("platform",""), ("","","#e94560",""))[2]

        header = tk.Frame(self.lobby_panel, bg=BG_CARD)
        header.pack(fill="x")

        tk.Label(header, text=f"🎮 {l.get('name','')}",
            font=(FONT, 10, "bold"), bg=BG_CARD, fg=TEXT).pack(side="left")
        tk.Button(header, text="Quitter",
            font=(FONT, 8), bg=RED, fg="white",
            relief="flat", padx=8, pady=2, cursor="hand2",
            command=self._leave_lobby).pack(side="right")

        # Players list
        players = l.get("players", [])
        pf = tk.Frame(self.lobby_panel, bg=BG_CARD)
        pf.pack(fill="x", pady=4)
        for p in players:
            is_host = p.get("isHost", False)
            is_me   = p.get("isMe", False)
            name    = p.get("username", "?")
            suffix  = " 👑" if is_host else ""
            suffix += " (vous)" if is_me else ""
            lbl_color = ACCENT if is_me else TEXT
            tk.Label(pf, text=f"  {name}{suffix}",
                font=(FONT, 8), bg=BG_CARD, fg=lbl_color).pack(anchor="w")

        self.lobby_panel.pack(fill="x", pady=4)

    def _hide_current_lobby(self):
        self.lobby_panel.pack_forget()

    # ── Devices ──────────────────────────────────────────────────────────────

    def _scan_network(self):
        self._log("Scan réseau en cours...")
        devs = scan_network()
        emus = detect_emulators()
        # Normalize to dicts
        def to_dict(d):
            if isinstance(d, dict):
                return d
            return {k: getattr(d, k, "") for k in ["ip","mac","manufacturer","console_type","type","platform"]}
        self.devices = [to_dict(d) for d in devs + emus]
        self.after(0, self._render_devices)
        self._log(f"Scan terminé: {len(devs)} appareils, {len(emus)} émulateurs")

    def _render_devices(self):
        for w in self.device_list.winfo_children():
            w.destroy()

        if not self.devices:
            tk.Label(self.device_list, text="Aucun appareil",
                font=(FONT, 8), bg=BG_CARD, fg=TEXT_DIM, pady=8).pack()
            return

        self._device_rows = []
        for dev in self.devices[:12]:
            ct   = dev.get("console_type", dev.get("type", "Unknown"))
            ip   = dev.get("ip", "")
            mac  = dev.get("mac", "")
            plat = dev.get("platform", self._guess_platform(ct))

            row = tk.Frame(self.device_list, bg=BG_ITEM, pady=3, padx=6, cursor="hand2")
            row.pack(fill="x", pady=1)

            icon = "🎮" if ct != "Unknown" else "💻"
            lbl_name = tk.Label(row, text=f"{icon} {ct}",
                font=(FONT, 8, "bold"), bg=BG_ITEM,
                fg=TEXT if ct != "Unknown" else TEXT_DIM)
            lbl_name.pack(anchor="w")
            lbl_ip = tk.Label(row, text=ip,
                font=("Consolas", 7), bg=BG_ITEM, fg=TEXT_DIM)
            lbl_ip.pack(anchor="w")

            # Click to select
            def make_select(d=dev, r=row, ln=lbl_name, li=lbl_ip, p=plat):
                def _select(e=None):
                    # Reset all rows
                    for rr, ll1, ll2 in self._device_rows:
                        rr.configure(bg=BG_ITEM)
                        ll1.configure(bg=BG_ITEM)
                        ll2.configure(bg=BG_ITEM)
                    # Highlight selected
                    r.configure(bg=BG_SEL)
                    ln.configure(bg=BG_SEL, fg=ACCENT)
                    li.configure(bg=BG_SEL)
                    # Switch platform
                    if p:
                        self._select_platform(p)
                    ct_key = "console_type"; ip_key = "ip"; self._log(f"Console selectionnee: {d.get(ct_key, chr(63))} @ {d.get(ip_key, chr(63))}")
                return _select

            fn = make_select()
            row.bind("<Button-1>", fn)
            lbl_name.bind("<Button-1>", fn)
            lbl_ip.bind("<Button-1>", fn)
            self._device_rows.append((row, lbl_name, lbl_ip))

    def _guess_platform(self, console_type: str) -> str:
        """Guess platform ID from console type string"""
        ct = console_type.lower()
        if "switch" in ct: return "switch"
        if "ps5" in ct: return "ps3"  # PS5 uses PS3 protocol for now
        if "ps4" in ct: return "ps3"
        if "ps3" in ct: return "ps3"
        if "ps2" in ct: return "ps2"
        if "psp" in ct: return "psp"
        if "vita" in ct: return "vita"
        if "xbox one" in ct: return "xboxone"
        if "xbox 360" in ct: return "xbox360"
        if "xbox" in ct: return "xbox"
        if "gamecube" in ct or "game cube" in ct: return "gamecube"
        if "wii" in ct: return "wii"
        return ""

    def _add_manual_device(self):
        ip   = self.entry_manual_ip.get().strip()
        plat = self.manual_platform.get()
        if not ip or ip == "IP de la console":
            messagebox.showwarning("Erreur", "Entrez une IP valide.")
            return

        pinfo = PLATFORM_MAP.get(plat, ("", plat, ACCENT, ""))
        dev = {
            "ip": ip,
            "mac": "manual",
            "console_type": pinfo[1],
            "platform": plat,
            "manual": True
        }
        self.devices.append(dev)
        self._render_devices()
        self._log(f"Appareil ajouté manuellement: {pinfo[1]} @ {ip}")

    # ── Relay ─────────────────────────────────────────────────────────────────

    def _toggle_relay(self):
        if self.relay.running:
            self.relay.disconnect()
            self.btn_relay.configure(text="Connecter au relay", bg=ACCENT)
            self.lbl_relay.configure(text="Non connecté", fg=TEXT_DIM)
        else:
            self.relay.set_platform(self.platform)
            ok = self.relay.connect()
            if ok:
                self.btn_relay.configure(text="⏹ Déconnecter", bg="#555")
                self.lbl_relay.configure(text=f"Connecté — relay NM EU", fg=GREEN)
            else:
                self.lbl_relay.configure(text="Erreur connexion", fg=RED)

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _show_login(self):
        def _result(ok, msg):
            if ok:
                self.after(0, self._update_user_display)
                self.after(0, self._connect_to_server)
                self.after(0, lambda: self._log(f"Connecté: {self.auth.username}"))
            else:
                self.after(0, lambda: self._log(f"Login: {msg}"))

        self._log("Ouverture navigateur → network-memories.com...")
        threading.Thread(target=self.auth.login_browser, args=(_result,), daemon=True).start()

    def _update_user_display(self):
        if self.auth.is_logged_in():
            self.btn_user.configure(
                text=f"● {self.auth.username} ▾",
                bg=BG_SEL, fg=GREEN,
                command=self._user_menu)

    def _user_menu(self):
        menu = tk.Menu(self, tearoff=0, bg=BG_CARD, fg=TEXT, activebackground=ACCENT)
        menu.add_command(label=f"👤 {self.auth.username}", state="disabled")
        menu.add_separator()
        menu.add_command(label="Se déconnecter", command=self._logout)
        menu.post(self.btn_user.winfo_rootx(),
                  self.btn_user.winfo_rooty() + self.btn_user.winfo_height())

    def _logout(self):
        if self.current_lobby:
            self._leave_lobby()
        self.auth.logout()
        self.btn_user.configure(text="Connexion", bg=ACCENT, command=self._show_login)
        self._log("Déconnecté")

    def _connect_to_server(self):
        """Register with NM-Play server after login"""
        if not self.auth.token:
            return
        def _do():
            result = self.api.connect(self.platform, self.auth.token)
            if result and result.get("ok"):
                self._log(f"Connecté au serveur NM-Play")
                self._start_heartbeat()
            else:
                self._log(f"Erreur connexion serveur")
        threading.Thread(target=_do, daemon=True).start()

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    def _start_heartbeat(self):
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _heartbeat_loop(self):
        while getattr(self, "_heartbeat_running", False):
            try:
                if self.auth.token:
                    self.api.heartbeat(self.auth.token)
            except Exception:
                pass
            time.sleep(25)

    # ── Server check ──────────────────────────────────────────────────────────

    def _check_server(self):
        def _do():
            try:
                h = self.api.health()
                if h and h.get("status") == "ok":
                    self.after(0, lambda: self.lbl_server.configure(
                        text="● Serveur NM OK", fg=GREEN))
                else:
                    self.after(0, lambda: self.lbl_server.configure(
                        text="● Serveur hors ligne", fg=RED))
            except Exception:
                self.after(0, lambda: self.lbl_server.configure(
                    text="● Serveur inaccessible", fg=RED))
        threading.Thread(target=_do, daemon=True).start()

    # ── Auto refresh ──────────────────────────────────────────────────────────

    def _start_refresh(self):
        self._refresh_lobbies()
        threading.Thread(target=self._scan_network, daemon=True).start()
        self.after(15000, self._auto_refresh)

    def _auto_refresh(self):
        self._refresh_lobbies()
        self._check_server()
        self.after(15000, self._auto_refresh)

    # ── Logs ──────────────────────────────────────────────────────────────────

    def _toggle_logs(self):
        self.show_logs = not self.show_logs
        if self.show_logs:
            self.log_frame.pack(fill="both", expand=True, padx=4, pady=4)
        else:
            self.log_frame.pack_forget()

    def _log(self, msg):
        def _do():
            self.log_text.configure(state="normal")
            ts = time.strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{ts}] {msg}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
            self.lbl_status.configure(text=msg[:80])
        self.after(0, _do)

    # ── Close ─────────────────────────────────────────────────────────────────

    def _on_close(self):
        self._heartbeat_running = False
        # Force sync disconnect before closing
        token = getattr(self.auth, "token", None)
        if token:
            import urllib.request, urllib.error
            for endpoint in ["/lobbies/current/leave", "/disconnect"]:
                try:
                    body = b"{}"
                    req = urllib.request.Request(
                        f"{self.api.base}{endpoint}",
                        data=body,
                        headers={"Content-Type":"application/json","Authorization":f"Bearer {token}"},
                        method="POST")
                    urllib.request.urlopen(req, timeout=2)
                except Exception:
                    pass
        if self.relay.running:
            try:
                self.relay.disconnect()
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    app = NMPlay()
    app.mainloop()