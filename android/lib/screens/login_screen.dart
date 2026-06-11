import "package:flutter/material.dart";
import "package:shared_preferences/shared_preferences.dart";
import "package:flutter_web_auth_2/flutter_web_auth_2.dart";
import "package:url_launcher/url_launcher.dart";
import "../core/api_service.dart";
import "../core/config.dart";
import "home_screen.dart";

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _loading = false;
  bool _obscure = true;
  String _error = "";

  Future<void> _saveAndGo(Map<String, dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString("nm_token", data["token"] ?? "");
    await prefs.setString("nm_username", data["username"] ?? "");
    if (mounted) {
      Navigator.pushReplacement(context,
          MaterialPageRoute(builder: (_) => const HomeScreen()));
    }
  }

  Future<void> _loginNM() async {
    if (_userCtrl.text.isEmpty || _passCtrl.text.isEmpty) {
      setState(() => _error = "Identifiant et mot de passe requis.");
      return;
    }
    setState(() { _loading = true; _error = ""; });
    final result = await ApiService.login(_userCtrl.text.trim(), _passCtrl.text.trim());
    setState(() => _loading = false);
    if (result != null) {
      await _saveAndGo(result);
    } else {
      setState(() => _error = "Identifiant ou mot de passe incorrect.");
    }
  }

  Future<void> _loginDiscord() async {
    if (NMConfig.discordClientId.isEmpty) {
      setState(() => _error = "Discord non configure dans cette version.");
      return;
    }
    setState(() { _loading = true; _error = ""; });
    try {
      final result = await FlutterWebAuth2.authenticate(
        url: NMConfig.discordAuthUrl,
        callbackUrlScheme: "nmplay",
      );
      final code = Uri.parse(result).queryParameters["code"];
      if (code != null) {
        final data = await ApiService.loginDiscord(code);
        if (data != null) {
          await _saveAndGo(data);
          return;
        }
      }
      setState(() => _error = "Connexion Discord echouee.");
    } catch (e) {
      setState(() => _error = "Erreur Discord: $e");
    }
    setState(() => _loading = false);
  }

  Future<void> _createAccount() async {
    final url = Uri.parse("${NMConfig.authUrl.replaceAll("/api/auth", "")}/register");
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 50),
              RichText(
                textAlign: TextAlign.center,
                text: const TextSpan(children: [
                  TextSpan(text: "NM", style: TextStyle(
                      fontSize: 42, fontWeight: FontWeight.bold, color: Color(0xFFE94560))),
                  TextSpan(text: "-Play", style: TextStyle(
                      fontSize: 42, fontWeight: FontWeight.bold, color: Color(0xFFEAEAEA))),
                ]),
              ),
              const SizedBox(height: 4),
              const Text("NetworkMemories", textAlign: TextAlign.center,
                  style: TextStyle(color: Color(0xFF8888AA), fontSize: 13)),
              const SizedBox(height: 48),

              // NM Login
              const Text("Connexion", style: TextStyle(
                  fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFFEAEAEA))),
              const SizedBox(height: 16),
              TextField(
                controller: _userCtrl,
                decoration: const InputDecoration(
                  labelText: "Identifiant",
                  prefixIcon: Icon(Icons.person_outline, color: Color(0xFF8888AA)),
                ),
                style: const TextStyle(color: Color(0xFFEAEAEA)),
                textInputAction: TextInputAction.next,
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _passCtrl,
                obscureText: _obscure,
                decoration: InputDecoration(
                  labelText: "Mot de passe",
                  prefixIcon: const Icon(Icons.lock_outline, color: Color(0xFF8888AA)),
                  suffixIcon: IconButton(
                    icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility,
                        color: const Color(0xFF8888AA)),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),
                style: const TextStyle(color: Color(0xFFEAEAEA)),
                onSubmitted: (_) => _loginNM(),
              ),
              if (_error.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(_error, style: const TextStyle(color: Color(0xFFE94560), fontSize: 12)),
              ],
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _loading ? null : _loginNM,
                  child: _loading
                      ? const SizedBox(height: 20, width: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text("Se connecter", style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                ),
              ),
              const SizedBox(height: 12),

              // Discord
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _loading ? null : _loginDiscord,
                  icon: const Icon(Icons.discord, color: Color(0xFF5865F2)),
                  label: const Text("Continuer avec Discord",
                      style: TextStyle(color: Color(0xFFEAEAEA))),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0xFF5865F2)),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
              const SizedBox(height: 12),

              // Divider
              Row(children: [
                const Expanded(child: Divider(color: Color(0xFF333355))),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 12),
                  child: Text("ou", style: TextStyle(color: Color(0xFF8888AA), fontSize: 12)),
                ),
                const Expanded(child: Divider(color: Color(0xFF333355))),
              ]),
              const SizedBox(height: 12),

              // Creer compte
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _createAccount,
                  icon: const Icon(Icons.person_add_outlined, color: Color(0xFF00C896)),
                  label: const Text("Creer un compte NM",
                      style: TextStyle(color: Color(0xFF00C896))),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0xFF00C896)),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
              const SizedBox(height: 12),

              // Sans compte
              TextButton(
                onPressed: () => Navigator.pushReplacement(context,
                    MaterialPageRoute(builder: (_) => const HomeScreen())),
                child: const Text("Continuer sans compte",
                    style: TextStyle(color: Color(0xFF8888AA), fontSize: 13)),
              ),
              const SizedBox(height: 32),
              const Text(
                "NM-Play ne tolere pas le piratage.\nPossedez legalement vos jeux.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Color(0xFF444466), fontSize: 11),
              ),
            ],
          ),
        ),
      ),
    );
  }
}