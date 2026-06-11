import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:shared_preferences/shared_preferences.dart";
import "screens/home_screen.dart";
import "screens/login_screen.dart";

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
  ));
  final prefs = await SharedPreferences.getInstance();
  final token = prefs.getString("nm_token");
  runApp(NMPlayApp(isLoggedIn: token != null));
}

class NMPlayApp extends StatelessWidget {
  final bool isLoggedIn;
  const NMPlayApp({super.key, required this.isLoggedIn});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "NM-Play",
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFE94560),
          secondary: Color(0xFF0F3460),
          surface: Color(0xFF1A1A2E),
          onSurface: Color(0xFFEAEAEA),
        ),
        scaffoldBackgroundColor: const Color(0xFF0F0F1A),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF1A1A2E),
          foregroundColor: Color(0xFFEAEAEA),
          elevation: 0,
        ),
        cardTheme: const CardThemeData(
          color: Color(0xFF1A1A2E),
          elevation: 0,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF16213E),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: BorderSide.none,
          ),
          labelStyle: const TextStyle(color: Color(0xFF8888AA)),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFFE94560),
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            padding: const EdgeInsets.symmetric(vertical: 14),
          ),
        ),
        fontFamily: "Roboto",
      ),
      home: isLoggedIn ? const HomeScreen() : const LoginScreen(),
    );
  }
}