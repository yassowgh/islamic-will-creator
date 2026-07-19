import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../main.dart' show kAppleSignInEnabled;

/// M1: language + disclaimer + auth. Auth providers are wired once
/// Firebase is configured; "Continue" works offline for the demo.
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  bool _accepted = false;
  String _language = 'en';

  static const disclaimer =
      'This tool does not constitute legal or religious advice. Have your '
      'will reviewed by a qualified solicitor and, for religious matters, '
      'a qualified scholar.';

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: ListView(
              shrinkWrap: true,
              padding: const EdgeInsets.all(24),
              children: [
                Text('Islamic Inheritance Will Creator',
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 4),
                const Text('England & Wales · wasiyya + faraid'),
                const SizedBox(height: 20),
                DropdownButtonFormField<String>(
                  value: _language,
                  decoration:
                      const InputDecoration(labelText: 'Language'),
                  items: const [
                    DropdownMenuItem(value: 'en', child: Text('English')),
                    DropdownMenuItem(
                        value: 'ar', child: Text('العربية (RTL)')),
                    DropdownMenuItem(value: 'ur', child: Text('اردو (RTL)')),
                    DropdownMenuItem(value: 'bn', child: Text('বাংলা')),
                  ],
                  onChanged: (v) => setState(() => _language = v ?? 'en'),
                ),
                const SizedBox(height: 16),
                CheckboxListTile(
                  value: _accepted,
                  onChanged: (v) =>
                      setState(() => _accepted = v ?? false),
                  title: const Text(disclaimer,
                      style: TextStyle(fontSize: 12)),
                ),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: _accepted
                      ? () => context.go('/wizard/profile')
                      : null,
                  child: const Text('Start my will'),
                ),
                const SizedBox(height: 20),
                const Divider(),
                const Text('Sign in (available once Firebase is set up):',
                    style: TextStyle(fontSize: 12)),
                const SizedBox(height: 8),
                Wrap(spacing: 8, children: [
                  OutlinedButton(
                      onPressed: null, child: const Text('Email')),
                  OutlinedButton(
                      onPressed: null, child: const Text('Phone OTP')),
                  OutlinedButton(
                      onPressed: null, child: const Text('Google')),
                  if (kAppleSignInEnabled)
                    OutlinedButton(
                        onPressed: null, child: const Text('Apple')),
                ]),
              ],
            ),
          ),
        ),
      );
}
