import "package:flutter/material.dart";
import "package:shared_preferences/shared_preferences.dart";
import "../core/api_service.dart";
import "../models/models.dart";
import "login_screen.dart";

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  String _username = "";
  String _platform = "switch";
  List<Lobby> _lobbies = [];
  List<DetectedDevice> _devices = [];
  bool _loadingLobbies = false;
  bool _serverOk = false;
  int _onlineCount = 0;
  late TabController _tabController;

  static const platforms = [
    ("switch",   "Switch",   Color(0xFFE4000F)),
    ("ps2",      "PS2",      Color(0xFF00439C)),
    ("ps3",      "PS3",      Color(0xFF003087)),
    ("psp",      "PSP",      Color(0xFF1A1A8C)),
    ("vita",     "Vita",     Color(0xFF003791)),
    ("xbox",     "Xbox",     Color(0xFF107C10)),
    ("xbox360",  "Xbox 360", Color(0xFF107C10)),
    ("gamecube", "GameCube", Color(0xFF6A0DAD)),
    ("wii",      "Wii",      Color(0xFFC0C0C0)),
    ("pc",       "PC LAN",   Color(0xFF00B4D8)),
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadUser();
    _checkServer();
    _refreshLobbies();
  }

  Future<void> _loadUser() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() => _username = prefs.getString("nm_username") ?? "");
  }

  Future<void> _checkServer() async {
    final ok = await ApiService.checkHealth();
    final stats = ok ? await ApiService.getStats() : {};
    setState(() {
      _serverOk = ok;
      _onlineCount = stats["online"] ?? 0;
    });
  }

  Future<void> _refreshLobbies() async {
    setState(() => _loadingLobbies = true);
    final lobbies = await ApiService.getLobbies(platform: _platform);
    setState(() { _lobbies = lobbies; _loadingLobbies = false; });
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove("nm_token");
    await prefs.remove("nm_username");
    if (mounted) Navigator.pushReplacement(context,
        MaterialPageRoute(builder: (_) => const LoginScreen()));
  }

  Future<void> _createLobby() async {
    if (_username.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Connecte-toi pour creer un lobby")));
      return;
    }
    final nameCtrl = TextEditingController();
    final gameCtrl = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1A1A2E),
        title: const Text("Creer un lobby", style: TextStyle(color: Color(0xFFEAEAEA))),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: nameCtrl,
              decoration: const InputDecoration(labelText: "Nom du lobby"),
              style: const TextStyle(color: Color(0xFFEAEAEA))),
          const SizedBox(height: 8),
          TextField(controller: gameCtrl,
              decoration: const InputDecoration(labelText: "Jeu"),
              style: const TextStyle(color: Color(0xFFEAEAEA))),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false),
              child: const Text("Annuler", style: TextStyle(color: Color(0xFF8888AA)))),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true),
              child: const Text("Creer")),
        ],
      ),
    );
    if (result == true && nameCtrl.text.isNotEmpty) {
      await ApiService.createLobby(
        name: nameCtrl.text, game: gameCtrl.text,
        platform: _platform, username: _username,
      );
      _refreshLobbies();
    }
  }

  Future<void> _joinLobby(Lobby lobby) async {
    if (_username.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Connecte-toi pour rejoindre un lobby")));
      return;
    }
    final result = await ApiService.joinLobby(
        lobbyId: lobby.id, username: _username, platform: _platform);
    if (result != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Lobby rejoint : ${lobby.name}")));
      _refreshLobbies();
    }
  }

  Color _platformColor(String pid) {
    for (final p in platforms) { if (p.$1 == pid) return p.$3; }
    return const Color(0xFFE94560);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: RichText(text: const TextSpan(children: [
          TextSpan(text: "NM", style: TextStyle(
              fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFFE94560))),
          TextSpan(text: "-Play", style: TextStyle(
              fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFFEAEAEA))),
        ])),
        actions: [
          // Server status
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
            child: Container(
              width: 8, height: 8,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _serverOk ? const Color(0xFF00C896) : const Color(0xFFE94560),
              ),
            ),
          ),
          // Online count
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Center(child: Text("$_onlineCount en ligne",
                style: const TextStyle(color: Color(0xFF8888AA), fontSize: 12))),
          ),
          // User menu
          PopupMenuButton<String>(
            icon: Icon(_username.isEmpty ? Icons.person_outline : Icons.person,
                color: _username.isEmpty ? const Color(0xFF8888AA) : const Color(0xFF00C896)),
            color: const Color(0xFF1A1A2E),
            onSelected: (v) { if (v == "logout") _logout(); },
            itemBuilder: (_) => [
              PopupMenuItem(enabled: false,
                  child: Text(_username.isEmpty ? "Non connecte" : _username,
                      style: const TextStyle(color: Color(0xFF8888AA)))),
              const PopupMenuDivider(),
              if (_username.isNotEmpty)
                const PopupMenuItem(value: "logout",
                    child: Text("Deconnexion", style: TextStyle(color: Color(0xFFE94560)))),
            ],
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: const Color(0xFFE94560),
          tabs: const [
            Tab(icon: Icon(Icons.games), text: "Lobbies"),
            Tab(icon: Icon(Icons.devices), text: "Consoles"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [_buildLobbiesTab(), _buildDevicesTab()],
      ),
      floatingActionButton: _tabController.index == 0
          ? FloatingActionButton.extended(
              onPressed: _createLobby,
              backgroundColor: const Color(0xFFE94560),
              icon: const Icon(Icons.add),
              label: const Text("Creer"),
            )
          : null,
    );
  }

  Widget _buildLobbiesTab() {
    return Column(children: [
      // Platform selector
      SizedBox(
        height: 44,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
          itemCount: platforms.length,
          itemBuilder: (_, i) {
            final p = platforms[i];
            final selected = p.$1 == _platform;
            return GestureDetector(
              onTap: () { setState(() => _platform = p.$1); _refreshLobbies(); },
              child: Container(
                margin: const EdgeInsets.only(right: 6),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: selected ? p.$3 : const Color(0xFF16213E),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Text(p.$2, style: TextStyle(
                  color: selected ? Colors.white : const Color(0xFF8888AA),
                  fontSize: 12, fontWeight: FontWeight.bold,
                )),
              ),
            );
          },
        ),
      ),
      // Lobbies list
      Expanded(
        child: _loadingLobbies
            ? const Center(child: CircularProgressIndicator(color: Color(0xFFE94560)))
            : _lobbies.isEmpty
                ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    const Icon(Icons.videogame_asset_off, color: Color(0xFF333355), size: 48),
                    const SizedBox(height: 12),
                    const Text("Aucun lobby actif", style: TextStyle(color: Color(0xFF8888AA))),
                    const SizedBox(height: 8),
                    TextButton(onPressed: _createLobby,
                        child: const Text("Soyez le premier !", style: TextStyle(color: Color(0xFFE94560)))),
                  ]))
                : RefreshIndicator(
                    onRefresh: _refreshLobbies,
                    color: const Color(0xFFE94560),
                    child: ListView.builder(
                      padding: const EdgeInsets.all(8),
                      itemCount: _lobbies.length,
                      itemBuilder: (_, i) => _buildLobbyCard(_lobbies[i]),
                    ),
                  ),
      ),
    ]);
  }

  Widget _buildLobbyCard(Lobby lobby) {
    final color = _platformColor(lobby.platform);
    final pct = lobby.players.length / lobby.maxPlayers;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: () => _joinLobby(lobby),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(children: [
            Container(width: 4, height: 48,
                decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(2))),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text(lobby.name, style: const TextStyle(
                    color: Color(0xFFEAEAEA), fontWeight: FontWeight.bold)),
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(color: color.withAlpha(51),
                      borderRadius: BorderRadius.circular(4)),
                  child: Text(lobby.platform.toUpperCase(),
                      style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold)),
                ),
              ]),
              if (lobby.game.isNotEmpty)
                Text(lobby.game, style: const TextStyle(color: Color(0xFF8888AA), fontSize: 12)),
              const SizedBox(height: 4),
              LinearProgressIndicator(value: pct,
                  backgroundColor: const Color(0xFF16213E),
                  valueColor: AlwaysStoppedAnimation(lobby.isFull ? const Color(0xFFE94560) : const Color(0xFF00C896))),
            ])),
            const SizedBox(width: 12),
            Text("${lobby.players.length}/${lobby.maxPlayers}",
                style: TextStyle(
                  color: lobby.isFull ? const Color(0xFFE94560) : const Color(0xFF00C896),
                  fontWeight: FontWeight.bold, fontSize: 16,
                )),
          ]),
        ),
      ),
    );
  }

  Widget _buildDevicesTab() {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: Row(children: [
          const Icon(Icons.info_outline, color: Color(0xFF8888AA), size: 16),
          const SizedBox(width: 8),
          const Expanded(child: Text("Consoles detectees sur votre reseau local",
              style: TextStyle(color: Color(0xFF8888AA), fontSize: 12))),
          TextButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.refresh, size: 16),
            label: const Text("Scanner"),
            style: TextButton.styleFrom(foregroundColor: const Color(0xFFE94560)),
          ),
        ]),
      ),
      Expanded(
        child: _devices.isEmpty
            ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                const Icon(Icons.devices_other, color: Color(0xFF333355), size: 48),
                const SizedBox(height: 12),
                const Text("Aucune console detectee", style: TextStyle(color: Color(0xFF8888AA))),
                const SizedBox(height: 4),
                const Text("Connectez votre console au meme reseau WiFi",
                    style: TextStyle(color: Color(0xFF555577), fontSize: 12)),
              ]))
            : ListView.builder(
                padding: const EdgeInsets.all(8),
                itemCount: _devices.length,
                itemBuilder: (_, i) => _buildDeviceCard(_devices[i]),
              ),
      ),
    ]);
  }

  Widget _buildDeviceCard(DetectedDevice dev) {
    final color = {
      "Nintendo": const Color(0xFF00C896),
      "Sony": const Color(0xFF4FC3F7),
      "Microsoft": const Color(0xFF107C10),
    }[dev.manufacturer] ?? const Color(0xFF8888AA);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withAlpha(51),
          child: Icon(Icons.gamepad, color: color),
        ),
        title: Text(dev.customName.isEmpty ? dev.consoleType : dev.customName,
            style: const TextStyle(color: Color(0xFFEAEAEA), fontWeight: FontWeight.bold)),
        subtitle: Text("${dev.ip} • ${dev.mac}",
            style: const TextStyle(color: Color(0xFF8888AA), fontSize: 11)),
        trailing: IconButton(
          icon: const Icon(Icons.edit, color: Color(0xFF8888AA), size: 18),
          onPressed: () => _nameDevice(dev),
        ),
      ),
    );
  }

  Future<void> _nameDevice(DetectedDevice dev) async {
    final nameCtrl = TextEditingController(text: dev.customName);
    final userCtrl = TextEditingController(text: dev.nmUser);
    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1A1A2E),
        title: Text("Nommer ${dev.consoleType}",
            style: const TextStyle(color: Color(0xFFEAEAEA))),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: nameCtrl,
              decoration: const InputDecoration(labelText: "Nom de la console"),
              style: const TextStyle(color: Color(0xFFEAEAEA))),
          const SizedBox(height: 8),
          TextField(controller: userCtrl,
              decoration: const InputDecoration(labelText: "User NM assigne"),
              style: const TextStyle(color: Color(0xFFEAEAEA))),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx),
              child: const Text("Annuler", style: TextStyle(color: Color(0xFF8888AA)))),
          ElevatedButton(
            onPressed: () {
              setState(() {
                dev.customName = nameCtrl.text;
                dev.nmUser = userCtrl.text;
              });
              Navigator.pop(ctx);
            },
            child: const Text("Sauvegarder"),
          ),
        ],
      ),
    );
  }
}