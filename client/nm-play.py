#!/usr/bin/env python3
"""
NM-Play — Universal LAN Play Launcher
NetworkMemories — networkmemories.com
"""

import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.api import get_health, get_stats, get_lobbies, create_lobby, join_lobby
from core.auth import NMAuth
from core.relay import RelayManager
from core.network import scan_network, detect_emulators

APP_NAME    = "NM-Play"
APP_VERSION = "1.0.0"

BG_DARK  = "#0f0f1a"
BG_CARD  = "#1a1a2e"
BG_CARD2 = "#16213e"
BG_ITEM  = "#0d1b2a"
ACCENT   = "#e94560"
ACCENT2  = "#0f3460"
TEXT     = "#eaeaea"
TEXT_DIM = "#8888aa"
GREEN    = "#00c896"
RED      = "#e94560"
YELLOW   = "#f5a623"
BLUE     = "#4fc3f7"

PLATFORMS = [
    ("switch",   "Switch"),
    ("ps2",      "PS2"),
    ("ps3",      "PS3"),
    ("psp",      "PSP"),
    ("vita",     "Vita"),
    ("xbox",     "Xbox"),
    ("xbox360",  "Xbox 360"),
    ("gamecube", "GameCube"),
    ("wii",      "Wii"),
    ("pc",       "PC LAN"),
]

PLATFORM_COLORS = {
    "switch":   "#e4000f",
    "ps2":      "#00439c",
    "ps3":      "#003087",
    "psp":      "#1a1a8c",
    "vita":     "#003791",
    "xbox":     "#107c10",
    "xbox360":  "#107c10",
    "gamecube": "#6a0dad",
    "wii":      "#c0c0c0",
    "pc":       "#00b4d8",
}


class NMPlay(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("900x620")
        self.minsize(800, 560)
        self.configure(bg=BG_DARK)

        self.auth    = NMAuth()
        self.relay   = RelayManager(log_callback=self._log)
        self.current_platform = "switch"
        self.lobbies = []
        self.devices = []

        self._build_ui()
        self._check_server()
        self._refresh_lobbies()

        if self.auth.is_logged_in():
            self._update_user_display()
        else:
            self.after(500, self._show_login)

        self.after(15000, self._auto_refresh)
        threading.Thread(target=self._scan_network, daemon=True).start()

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_CARD, pady=10)
        header.pack(fill="x")

        left = tk.Frame(header, bg=BG_CARD)
        left.pack(side="left", padx=16)
        tk.Label(left, text="NM", font=("Segoe UI", 22, "bold"),
                 bg=BG_CARD, fg=ACCENT).pack(side="left")
        tk.Label(left, text="-Play", font=("Segoe UI", 22, "bold"),
                 bg=BG_CARD, fg=TEXT).pack(side="left")
        tk.Label(left, text=f"  v{APP_VERSION}",
                 font=("Segoe UI", 9), bg=BG_CARD, fg=TEXT_DIM).pack(side="left", pady=6)

        right = tk.Frame(header, bg=BG_CARD)
        right.pack(side="right", padx=16)

        self.lbl_server = tk.Label(right, text="Serveur: ...",
                                    font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_DIM)
        self.lbl_server.pack(side="right", padx=8)

        self.btn_user = tk.Button(right, text="Connexion",
                                   font=("Segoe UI", 9, "bold"),
                                   bg=ACCENT, fg="white", relief="flat",
                                   padx=10, pady=4, cursor="hand2",
                                   command=self._show_login)
        self.btn_user.pack(side="right", padx=4)

        # ── Platform tabs ────────────────────────────────────────────
        tab_frame = tk.Frame(self, bg=BG_CARD2, pady=6)
        tab_frame.pack(fill="x")

        self.platform_btns = {}
        for pid, pname in PLATFORMS:
            color = PLATFORM_COLORS.get(pid, ACCENT)
            btn = tk.Button(tab_frame, text=pname,
                            font=("Segoe UI", 8, "bold"),
                            bg=BG_CARD2, fg=TEXT_DIM,
                            relief="flat", padx=8, pady=4,
                            cursor="hand2",
                            command=lambda p=pid: self._select_platform(p))
            btn.pack(side="left", padx=2)
            self.platform_btns[pid] = btn

        self._select_platform("switch")

        # ── Main content ─────────────────────────────────────────────
        main = tk.Frame(self, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=8, pady=4)

        # Left column — lobbies + devices
        left_col = tk.Frame(main, bg=BG_DARK)
        left_col.pack(side="left", fill="both", expand=True)

        # Lobby header
        lobby_header = tk.Frame(left_col, bg=BG_DARK)
        lobby_header.pack(fill="x", pady=(4, 2))

        tk.Label(lobby_header, text="Lobbies actifs",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_DARK, fg=TEXT).pack(side="left")

        self.lbl_online = tk.Label(lobby_header, text="0 en ligne",
                                    font=("Segoe UI", 8),
                                    bg=BG_DARK, fg=GREEN)
        self.lbl_online.pack(side="left", padx=8)

        tk.Button(lobby_header, text="Actualiser",
                  font=("Segoe UI", 8), bg=BG_CARD2, fg=TEXT_DIM,
                  relief="flat", padx=6, pady=2, cursor="hand2",
                  command=self._refresh_lobbies).pack(side="right")

        # Lobby list
        lobby_frame = tk.Frame(left_col, bg=BG_CARD, bd=0)
        lobby_frame.pack(fill="both", expand=True, pady=2)

        self.lobby_canvas = tk.Canvas(lobby_frame, bg=BG_CARD,
                                       highlightthickness=0)
        scrollbar = ttk.Scrollbar(lobby_frame, orient="vertical",
                                   command=self.lobby_canvas.yview)
        self.lobby_list = tk.Frame(self.lobby_canvas, bg=BG_CARD)

        self.lobby_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.lobby_canvas.pack(side="left", fill="both", expand=True)
        self.lobby_canvas.create_window((0, 0), window=self.lobby_list,
                                         anchor="nw", tags="frame")
        self.lobby_list.bind("<Configure>",
            lambda e: self.lobby_canvas.configure(
                scrollregion=self.lobby_canvas.bbox("all")))

        # Lobby action buttons
        btn_row = tk.Frame(left_col, bg=BG_DARK)
        btn_row.pack(fill="x", pady=4)

        tk.Button(btn_row, text="+ Créer un lobby",
                  font=("Segoe UI", 9, "bold"),
                  bg=ACCENT, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2",
                  command=self._create_lobby).pack(side="left", padx=2)

        tk.Button(btn_row, text="→ Rejoindre",
                  font=("Segoe UI", 9, "bold"),
                  bg=ACCENT2, fg="white", relief="flat",
                  padx=12, pady=6, cursor="hand2",
                  command=self._join_lobby).pack(side="left", padx=2)

        # Right column — devices + log
        right_col = tk.Frame(main, bg=BG_DARK, width=280)
        right_col.pack(side="right", fill="y", padx=(4, 0))
        right_col.pack_propagate(False)

        # Devices panel
        dev_frame = tk.LabelFrame(right_col, text=" Consoles détectées ",
                                   bg=BG_DARK, fg=TEXT_DIM,
                                   font=("Segoe UI", 8),
                                   padx=4, pady=4)
        dev_frame.pack(fill="x", pady=(0, 4))

        self.device_list = tk.Frame(dev_frame, bg=BG_DARK)
        self.device_list.pack(fill="x")

        tk.Button(dev_frame, text="Scanner le réseau",
                  font=("Segoe UI", 8), bg=BG_CARD2, fg=TEXT_DIM,
                  relief="flat", padx=6, pady=2, cursor="hand2",
                  command=lambda: threading.Thread(
                      target=self._scan_network, daemon=True).start()
                  ).pack(pady=4)

        # Log panel
        log_frame = tk.LabelFrame(right_col, text=" Logs ",
                                   bg=BG_DARK, fg=TEXT_DIM,
                                   font=("Segoe UI", 8),
                                   padx=4, pady=4)
        log_frame.pack(fill="both", expand=True)

        self.log_box = scrolledtext.ScrolledText(
            log_frame, height=8, font=("Consolas", 7),
            bg="#0a0a14", fg="#88ff88",
            insertbackground="white", relief="flat", state="disabled"
        )
        self.log_box.pack(fill="both", expand=True)

        # ── Status bar ───────────────────────────────────────────────
        status = tk.Frame(self, bg=BG_CARD2, pady=4, padx=12)
        status.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(status, text="Déconnecté",
                                    font=("Segoe UI", 8),
                                    bg=BG_CARD2, fg=TEXT_DIM)
        self.lbl_status.pack(side="left")

        self.btn_relay = tk.Button(status, text="Connecter au relay",
                                    font=("Segoe UI", 8, "bold"),
                                    bg=ACCENT, fg="white", relief="flat",
                                    padx=8, pady=2, cursor="hand2",
                                    command=self._toggle_relay)
        self.btn_relay.pack(side="right")

        tk.Label(status,
                 text="NM-Play ne tolere pas le piratage. Possedez legalement vos jeux.",
                 font=("Segoe UI", 7), bg=BG_CARD2, fg=TEXT_DIM
                 ).pack(side="right", padx=16)

    # ── Platform selection ───────────────────────────────────────────

    def _select_platform(self, pid: str):
        self.current_platform = pid
        color = PLATFORM_COLORS.get(pid, ACCENT)
        for p, btn in self.platform_btns.items():
            if p == pid:
                btn.configure(bg=color, fg="white")
            else:
                btn.configure(bg=BG_CARD2, fg=TEXT_DIM)
        self._refresh_lobbies()

    # ── Lobby UI ─────────────────────────────────────────────────────

    def _refresh_lobbies(self):
        def _do():
            lobbies = get_lobbies(self.current_platform)
            self.lobbies = lobbies or []
            self.after(0, self._render_lobbies)
        threading.Thread(target=_do, daemon=True).start()

    def _render_lobbies(self):
        for w in self.lobby_list.winfo_children():
            w.destroy()

        if not self.lobbies:
            tk.Label(self.lobby_list,
                     text="Aucun lobby actif — soyez le premier !",
                     font=("Segoe UI", 9), bg=BG_CARD, fg=TEXT_DIM,
                     pady=20).pack()
            return

        for lobby in self.lobbies:
            self._render_lobby_item(lobby)

        total = sum(len(l.get("players", [])) for l in self.lobbies)
        self.lbl_online.configure(text=f"{total} joueur(s) en ligne")

    def _render_lobby_item(self, lobby: dict):
        color = PLATFORM_COLORS.get(lobby.get("platform", ""), ACCENT)
        players = lobby.get("players", [])
        max_p   = lobby.get("maxPlayers", 8)

        row = tk.Frame(self.lobby_list, bg=BG_ITEM,
                       pady=6, padx=8, cursor="hand2")
        row.pack(fill="x", padx=4, pady=2)

        # Color bar
        tk.Frame(row, bg=color, width=4).pack(side="left", fill="y", padx=(0, 8))

        info = tk.Frame(row, bg=BG_ITEM)
        info.pack(side="left", fill="both", expand=True)

        name_row = tk.Frame(info, bg=BG_ITEM)
        name_row.pack(fill="x")
        tk.Label(name_row, text=lobby.get("name", "Lobby"),
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_ITEM, fg=TEXT).pack(side="left")
        tk.Label(name_row,
                 text=f"  {lobby.get('platform','').upper()}",
                 font=("Segoe UI", 7),
                 bg=BG_ITEM, fg=color).pack(side="left")

        tk.Label(info, text=lobby.get("game", ""),
                 font=("Segoe UI", 8),
                 bg=BG_ITEM, fg=TEXT_DIM).pack(anchor="w")

        count_color = GREEN if len(players) < max_p else RED
        tk.Label(row, text=f"{len(players)}/{max_p}",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_ITEM, fg=count_color).pack(side="right")

        row.bind("<Double-Button-1>",
                 lambda e, lid=lobby.get("id"): self._join_lobby(lid))

    def _create_lobby(self):
        if not self.auth.is_logged_in():
            messagebox.showwarning("Connexion requise",
                                    "Connecte-toi avec ton compte NM pour créer un lobby.")
            self._show_login()
            return

        name = simpledialog.askstring("Créer un lobby", "Nom du lobby :")
        if not name:
            return
        game = simpledialog.askstring("Créer un lobby", "Nom du jeu :")
        if not game:
            return

        def _do():
            result = create_lobby(name, game, self.current_platform,
                                   self.auth.username or "Joueur")
            if result:
                self._log(f"Lobby créé : {name}")
                self.after(0, self._refresh_lobbies)
            else:
                self._log("Erreur lors de la création du lobby")
        threading.Thread(target=_do, daemon=True).start()

    def _join_lobby(self, lobby_id: str = None):
        if not self.auth.is_logged_in():
            messagebox.showwarning("Connexion requise",
                                    "Connecte-toi avec ton compte NM pour rejoindre un lobby.")
            self._show_login()
            return

        if lobby_id is None:
            sel = self.lobby_list.focus_get()
            if not self.lobbies:
                return
            lobby_id = self.lobbies[0].get("id")

        def _do():
            result = join_lobby(lobby_id, self.auth.username or "Joueur",
                                 self.current_platform)
            if result:
                self._log(f"Lobby rejoint !")
                if not self.relay.running:
                    self._toggle_relay()
            else:
                self._log("Impossible de rejoindre le lobby")
        threading.Thread(target=_do, daemon=True).start()

    # ── Relay ────────────────────────────────────────────────────────

    def _toggle_relay(self):
        if self.relay.running:
            self.relay.disconnect()
            self.btn_relay.configure(text="Connecter au relay", bg=ACCENT)
            self.lbl_status.configure(text="Déconnecté", fg=TEXT_DIM)
        else:
            self.relay.set_platform(self.current_platform)
            ok = self.relay.connect()
            if ok:
                self.btn_relay.configure(text="Déconnecter", bg="#555")
                self.lbl_status.configure(text=f"Connecté — relay NM", fg=GREEN)
            else:
                self.lbl_status.configure(text="Erreur connexion", fg=RED)

    # ── Auth ─────────────────────────────────────────────────────────

    def _show_login(self):
        def _on_login_result(ok, msg):
            if ok:
                self.after(0, self._update_user_display)
                self.after(0, lambda: self._log(f"Connecte en tant que {self.auth.username}"))
            else:
                self.after(0, lambda: self._log(f"Erreur login: {msg}"))

        self._log("Ouverture du navigateur pour connexion NM...")
        import threading
        threading.Thread(
            target=self.auth.login_browser,
            args=(_on_login_result,),
            daemon=True
        ).start()

    def _update_user_display(self):
        if self.auth.is_logged_in():
            self.btn_user.configure(
                text=f"{self.auth.username} ▾",
                bg=BG_CARD2, fg=TEXT,
                command=self._user_menu
            )

    def _user_menu(self):
        menu = tk.Menu(self, tearoff=0, bg=BG_CARD, fg=TEXT,
                       activebackground=ACCENT)
        menu.add_command(label=f"Connecté: {self.auth.username}", state="disabled")
        menu.add_separator()
        menu.add_command(label="Se déconnecter", command=self._logout)
        menu.post(self.btn_user.winfo_rootx(),
                  self.btn_user.winfo_rooty() + self.btn_user.winfo_height())

    def _logout(self):
        self.auth.logout()
        self.btn_user.configure(text="Connexion", bg=ACCENT,
                                 command=self._show_login)
        self._log("Déconnecté")

    # ── Network scan ─────────────────────────────────────────────────

    def _scan_network(self):
        self._log("Scan du réseau en cours...")
        devices = scan_network()
        emus    = detect_emulators()
        self.devices = devices
        self.after(0, lambda: self._render_devices(devices, emus))

    def _render_devices(self, devices, emus):
        for w in self.device_list.winfo_children():
            w.destroy()

        found = [d for d in devices if d.manufacturer != "Unknown"]

        if not found and not emus:
            tk.Label(self.device_list, text="Aucune console détectée",
                     font=("Segoe UI", 8), bg=BG_DARK, fg=TEXT_DIM).pack()
            return

        for dev in found:
            color = {"Nintendo": GREEN, "Sony": BLUE,
                     "Microsoft": "#107c10", "Valve": "#00b4d8"}.get(
                     dev.manufacturer, TEXT_DIM)
            row = tk.Frame(self.device_list, bg=BG_DARK)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"● {dev.console_type}",
                     font=("Segoe UI", 8, "bold"),
                     bg=BG_DARK, fg=color).pack(side="left")
            tk.Label(row, text=f" {dev.ip}",
                     font=("Segoe UI", 7),
                     bg=BG_DARK, fg=TEXT_DIM).pack(side="left")
            tk.Button(row, text="Nommer",
                      font=("Segoe UI", 7), bg=BG_CARD2, fg=TEXT_DIM,
                      relief="flat", cursor="hand2",
                      command=lambda d=dev: self._name_device(d)
                      ).pack(side="right")

        for emu in emus:
            row = tk.Frame(self.device_list, bg=BG_DARK)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"◈ {emu['name']}",
                     font=("Segoe UI", 8, "bold"),
                     bg=BG_DARK, fg=YELLOW).pack(side="left")

        self._log(f"Détecté: {len(found)} console(s), {len(emus)} émulateur(s)")

    def _name_device(self, dev):
        name = simpledialog.askstring("Nommer la console",
                                       f"Nom pour {dev.console_type} ({dev.ip}) :")
        if name:
            dev.custom_name = name
            user = simpledialog.askstring("Assigner à un joueur",
                                           f"User NM pour '{name}' :")
            if user:
                dev.nm_user = user
            self._log(f"Console nommée: {name} → {dev.nm_user or 'Non assigné'}")
            threading.Thread(
                target=self._scan_network, daemon=True).start()

    # ── Server check ─────────────────────────────────────────────────

    def _check_server(self):
        def _do():
            ok = get_health()
            stats = get_stats() if ok else {}
            status = "Serveur NM OK" if ok else "Serveur hors ligne"
            color  = GREEN if ok else RED
            online = stats.get("online", 0)
            self.after(0, lambda: self.lbl_server.configure(
                text=f"{status} — {online} joueurs", fg=color))
        threading.Thread(target=_do, daemon=True).start()

    def _auto_refresh(self):
        self._refresh_lobbies()
        self._check_server()
        self.after(15000, self._auto_refresh)

    # ── Log ──────────────────────────────────────────────────────────

    def _log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def on_close(self):
        if self.relay.running:
            self.relay.disconnect()
        self.destroy()


if __name__ == "__main__":
    app = NMPlay()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
