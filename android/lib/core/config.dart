class NMConfig {
  static const String relayHost = String.fromEnvironment("NM_RELAY_HOST", defaultValue: "localhost");
  static const int relayPort = int.fromEnvironment("NM_RELAY_PORT", defaultValue: 11451);
  static const String apiHost = String.fromEnvironment("NM_API_HOST", defaultValue: "localhost");
  static const int apiPort = int.fromEnvironment("NM_API_PORT", defaultValue: 8080);
  static const String authUrl = String.fromEnvironment("NM_AUTH_URL", defaultValue: "");
  static const String discordClientId = String.fromEnvironment("NM_DISCORD_CLIENT_ID", defaultValue: "");
  static const String discordRedirectUri = String.fromEnvironment("NM_DISCORD_REDIRECT", defaultValue: "");

  static String get apiBase => "http://$apiHost:$apiPort";
  static String get wsUrl => "ws://$apiHost:$apiPort/ws";
  static String get discordAuthUrl =>
      "https://discord.com/api/oauth2/authorize"
      "?client_id=$discordClientId"
      "&redirect_uri=${Uri.encodeComponent(discordRedirectUri)}"
      "&response_type=code"
      "&scope=identify%20email";

  static const String appName = "NM-Play";
  static const String appVersion = "1.0.0";
}