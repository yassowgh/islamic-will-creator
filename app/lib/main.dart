import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'router.dart';

// Feature flags (see README): Apple sign-in requires an Apple Developer
// account and is mandatory on iOS once other social logins ship.
const bool kAppleSignInEnabled = false;

void main() {
  // TODO(M1): Firebase.initializeApp + App Check activation.
  runApp(const ProviderScope(child: IwcApp()));
}

class IwcApp extends StatelessWidget {
  const IwcApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Islamic Will Creator',
      routerConfig: buildRouter(),
      supportedLocales: const [
        Locale('en'), Locale('ar'), Locale('ur'), Locale('bn'),
      ],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate, // provides RTL for ar/ur
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.teal),
    );
  }
}
