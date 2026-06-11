class Lobby {
  final String id;
  final String name;
  final String platform;
  final String game;
  final List<Player> players;
  final int maxPlayers;

  Lobby({
    required this.id,
    required this.name,
    required this.platform,
    required this.game,
    required this.players,
    required this.maxPlayers,
  });

  factory Lobby.fromJson(Map<String, dynamic> json) {
    return Lobby(
      id: json["id"] ?? "",
      name: json["name"] ?? "",
      platform: json["platform"] ?? "",
      game: json["game"] ?? "",
      players: (json["players"] as List? ?? [])
          .map((p) => Player.fromJson(p))
          .toList(),
      maxPlayers: json["maxPlayers"] ?? 8,
    );
  }

  bool get isFull => players.length >= maxPlayers;
}

class Player {
  final String id;
  final String username;
  final String platform;

  Player({required this.id, required this.username, required this.platform});

  factory Player.fromJson(Map<String, dynamic> json) {
    return Player(
      id: json["id"] ?? "",
      username: json["username"] ?? "",
      platform: json["platform"] ?? "",
    );
  }
}

class DetectedDevice {
  final String mac;
  final String ip;
  final String manufacturer;
  final String consoleType;
  String customName;
  String nmUser;

  DetectedDevice({
    required this.mac,
    required this.ip,
    required this.manufacturer,
    required this.consoleType,
    this.customName = "",
    this.nmUser = "",
  });
}