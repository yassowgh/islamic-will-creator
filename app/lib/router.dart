import 'package:go_router/go_router.dart';

import 'src/auth/onboarding_screen.dart';
import 'src/calculation/calculation_screen.dart';
import 'src/lifecycle/dashboard_screen.dart';
import 'src/wizard/wizard_screen.dart';

GoRouter buildRouter() => GoRouter(routes: [
      GoRoute(path: '/', builder: (c, s) => const OnboardingScreen()),
      GoRoute(path: '/wizard/:step', builder: (c, s) =>
          WizardScreen(step: s.pathParameters['step']!)),
      GoRoute(path: '/calculation/:willId', builder: (c, s) =>
          CalculationScreen(willId: s.pathParameters['willId']!)),
      GoRoute(path: '/dashboard', builder: (c, s) =>
          const DashboardScreen()),
    ]);
