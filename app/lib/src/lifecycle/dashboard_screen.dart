import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../state/providers.dart';

/// M4/M5: lifecycle tracker. Transitions are made server-side; this
/// screen renders statusHistory and offers the next action.
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  static const _steps = [
    (WillStatus.initiated, 'Draft', 'Complete the wizard.'),
    (WillStatus.finalized, 'Finalized',
        'Calculation locked; PDF generated.'),
    (WillStatus.downloaded, 'Downloaded', 'Print your will.'),
    (WillStatus.inSignature, 'Signing',
        'Sign before both witnesses, present together (s.9).'),
    (WillStatus.signedUploaded, 'Uploaded',
        'Scan uploaded; consistency check running.'),
    (WillStatus.signedUploadedVerified, 'Verified',
        'Checked and confirmed by an administrator.'),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final draft = ref.watch(willDraftProvider);
    final currentIndex =
        _steps.indexWhere((s) => s.$1 == draft.status).clamp(0, 5);
    return Scaffold(
      appBar: AppBar(title: const Text('My will')),
      body: Stepper(
        currentStep: currentIndex,
        controlsBuilder: (context, details) => const SizedBox.shrink(),
        steps: [
          for (final (i, s) in _steps.indexed)
            Step(
              title: Text(s.$2),
              content: Align(
                alignment: Alignment.centerLeft,
                child: Text(s.$3),
              ),
              isActive: i <= currentIndex,
              state: i < currentIndex
                  ? StepState.complete
                  : i == currentIndex
                      ? StepState.editing
                      : StepState.indexed,
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          // M5: opens the document scanner (cunning_document_scanner) on
          // mobile or a file picker on web, then uploads for OCR check.
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
              content: Text('Upload flow arrives with the M5 backend.')));
        },
        icon: const Icon(Icons.document_scanner),
        label: const Text('Upload signed will'),
      ),
    );
  }
}
