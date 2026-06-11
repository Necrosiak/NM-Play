import "dart:convert";
import "package:http/http.dart" as http;
import "../core/config.dart";
import "../models/models.dart";

class ApiService {
  static Future<bool> checkHealth() async {
    try {
      final r = await http.get(Uri.parse("${NMConfig.apiBase}/health"))
          .timeout(const Duration(seconds: 5));
      final data = jsonDecode(r.body);
      return data["status"] == "ok";
    } catch (_) { return false; }
  }

  static Future<Map<String, dynamic>> getStats() async {
    try {
      final r = await http.get(Uri.parse("${NMConfig.apiBase}/stats"))
          .timeout(const Duration(seconds: 5));
      return jsonDecode(r.body);
    } catch (_) { return {}; }
  }

  static Future<List<Lobby>> getLobbies({String platform = ""}) async {
    try {
      final url = platform.isEmpty
          ? "${NMConfig.apiBase}/lobbies"
          : "${NMConfig.apiBase}/lobbies?platform=$platform";
      final r = await http.get(Uri.parse(url))
          .timeout(const Duration(seconds: 5));
      final List data = jsonDecode(r.body);
      return data.map((e) => Lobby.fromJson(e)).toList();
    } catch (_) { return []; }
  }

  static Future<Lobby?> createLobby({
    required String name,
    required String game,
    required String platform,
    required String username,
    int maxPlayers = 8,
  }) async {
    try {
      final r = await http.post(
        Uri.parse("${NMConfig.apiBase}/lobbies"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "name": name, "game": game, "platform": platform,
          "username": username, "max_players": maxPlayers,
        }),
      ).timeout(const Duration(seconds: 5));
      return Lobby.fromJson(jsonDecode(r.body));
    } catch (_) { return null; }
  }

  static Future<Lobby?> joinLobby({
    required String lobbyId,
    required String username,
    required String platform,
  }) async {
    try {
      final r = await http.post(
        Uri.parse("${NMConfig.apiBase}/lobbies/$lobbyId/join"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"username": username, "platform": platform}),
      ).timeout(const Duration(seconds: 5));
      if (r.statusCode == 200) return Lobby.fromJson(jsonDecode(r.body));
      return null;
    } catch (_) { return null; }
  }

  static Future<Map<String, dynamic>?> loginDiscord(String code) async {
    if (NMConfig.authUrl.isEmpty) return null;
    try {
      final r = await http.post(
        Uri.parse("${NMConfig.authUrl}/discord"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"code": code}),
      ).timeout(const Duration(seconds: 5));
      if (r.statusCode == 200) return jsonDecode(r.body);
      return null;
    } catch (_) { return null; }
  }

  static Future<Map<String, dynamic>?> login(String username, String password) async {
    if (NMConfig.authUrl.isEmpty) return null;
    try {
      final r = await http.post(
        Uri.parse("${NMConfig.authUrl}/login"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"username": username, "password": password}),
      ).timeout(const Duration(seconds: 5));
      if (r.statusCode == 200) return jsonDecode(r.body);
      return null;
    } catch (_) { return null; }
  }
}