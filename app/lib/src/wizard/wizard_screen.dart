import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/models.dart';
import '../state/providers.dart';

/// The will-creation wizard (M3). Steps: profile -> estate -> wasiyya ->
/// heirs -> executor & witnesses -> review.
class WizardScreen extends ConsumerStatefulWidget {
  const WizardScreen({super.key, required this.step});
  final String step;

  @override
  ConsumerState<WizardScreen> createState() => _WizardScreenState();
}

class _WizardScreenState extends ConsumerState<WizardScreen> {
  static const steps = [
    'profile', 'estate', 'wasiyya', 'heirs', 'executor', 'review',
  ];

  int get index => steps.indexOf(widget.step).clamp(0, steps.length - 1);

  void _go(int i) =>
      context.go('/wizard/${steps[i.clamp(0, steps.length - 1)]}');

  @override
  Widget build(BuildContext context) {
    final draft = ref.watch(willDraftProvider);
    final notifier = ref.read(willDraftProvider.notifier);
    return Scaffold(
      appBar: AppBar(title: Text('Your will — step ${index + 1} of '
          '${steps.length}')),
      body: Column(children: [
        LinearProgressIndicator(value: (index + 1) / steps.length),
        const _DisclaimerBanner(),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: switch (widget.step) {
              'profile' => _ProfileStep(draft, notifier),
              'estate' => _EstateStep(draft, notifier),
              'wasiyya' => _WasiyyaStep(draft, notifier),
              'heirs' => _HeirsStep(draft, notifier),
              'executor' => _ExecutorStep(draft, notifier),
              _ => _ReviewStep(draft),
            },
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (index > 0)
                OutlinedButton(onPressed: () => _go(index - 1),
                    child: const Text('Back'))
              else
                const SizedBox.shrink(),
              FilledButton(
                onPressed: () => index == steps.length - 1
                    ? context.go('/calculation/draft')
                    : _go(index + 1),
                child: Text(index == steps.length - 1
                    ? 'Calculate shares'
                    : 'Next'),
              ),
            ],
          ),
        ),
      ]),
    );
  }
}

class _DisclaimerBanner extends StatelessWidget {
  const _DisclaimerBanner();
  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        color: Colors.amber.shade50,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: const Text(
          'This tool does not constitute legal or religious advice. Have '
          'your will reviewed by a qualified solicitor and, for religious '
          'matters, a qualified scholar.',
          style: TextStyle(fontSize: 12),
        ),
      );
}

class _ProfileStep extends StatelessWidget {
  const _ProfileStep(this.draft, this.notifier);
  final WillDraft draft;
  final WillDraftNotifier notifier;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextFormField(
            initialValue: draft.fullLegalName,
            decoration: const InputDecoration(labelText: 'Full legal name'),
            onChanged: (v) => notifier.update((d) => d.fullLegalName = v),
          ),
          TextFormField(
            initialValue: draft.address,
            decoration: const InputDecoration(labelText: 'Address'),
            onChanged: (v) => notifier.update((d) => d.address = v),
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<Madhhab>(
            value: draft.madhhab,
            decoration:
                const InputDecoration(labelText: 'School of law (madhhab)'),
            items: [
              for (final m in Madhhab.values)
                DropdownMenuItem(value: m, child: Text(m.label)),
            ],
            onChanged: (m) =>
                notifier.update((d) => d.madhhab = m ?? d.madhhab),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(draft.madhhab.explainer,
                style: Theme.of(context).textTheme.bodySmall),
          ),
        ],
      );
}

class _EstateStep extends StatelessWidget {
  const _EstateStep(this.draft, this.notifier);
  final WillDraft draft;
  final WillDraftNotifier notifier;

  Widget _money(String label, double value,
          void Function(WillDraft, double) set) =>
      TextFormField(
        initialValue: value == 0 ? '' : value.toStringAsFixed(0),
        keyboardType: TextInputType.number,
        decoration: InputDecoration(labelText: label, prefixText: '£ '),
        onChanged: (v) =>
            notifier.update((d) => set(d, double.tryParse(v) ?? 0)),
      );

  @override
  Widget build(BuildContext context) => Column(children: [
        _money('Estimated gross estate', draft.grossEstate,
            (d, v) => d.grossEstate = v),
        _money('Funeral cost estimate', draft.funeralCosts,
            (d, v) => d.funeralCosts = v),
        _money('Debts', draft.debts, (d, v) => d.debts = v),
        _money('Unpaid mahr owed', draft.unpaidMahr,
            (d, v) => d.unpaidMahr = v),
        _money('Unpaid zakat', draft.unpaidZakat,
            (d, v) => d.unpaidZakat = v),
        _money('Kaffarat / fidya', draft.kaffarat,
            (d, v) => d.kaffarat = v),
        const SizedBox(height: 12),
        Card(
          color: Colors.teal.shade50,
          child: const Padding(
            padding: EdgeInsets.all(12),
            child: Text(
              'A will cannot reach everything: joint-tenancy property '
              'passes to the co-owner by survivorship (a solicitor can '
              'sever to tenants-in-common); pensions and life insurance '
              'usually pass by nomination — update your pension '
              '"Expression of Wish" to match your faraid shares. Foreign '
              'assets may need a local will.',
              style: TextStyle(fontSize: 12),
            ),
          ),
        ),
      ]);
}

class _WasiyyaStep extends StatelessWidget {
  const _WasiyyaStep(this.draft, this.notifier);
  final WillDraft draft;
  final WillDraftNotifier notifier;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Wasiyya (bequest): '
              '${draft.wasiyyaPercent.toStringAsFixed(2)}% of net estate'),
          Slider(
            value: draft.wasiyyaPercent,
            max: 33.33, // hard cap - hadith of Sa'd ibn Abi Waqqas
            divisions: 3333,
            label: '${draft.wasiyyaPercent.toStringAsFixed(2)}%',
            onChanged: (v) =>
                notifier.update((d) => d.wasiyyaPercent = v),
          ),
          const Text(
            'You may leave up to one-third of your net estate to charity '
            'or non-heirs. "A third, and a third is much" (Bukhari 2742, '
            'Muslim 1628). Bequests to existing heirs classically require '
            'the other heirs\' consent after death — the generated will '
            'flags them.',
            style: TextStyle(fontSize: 12),
          ),
          TextFormField(
            initialValue: draft.wasiyyaRecipients,
            decoration: const InputDecoration(
                labelText: 'Recipients (charity + registered number, or '
                    'non-heir individuals)'),
            onChanged: (v) =>
                notifier.update((d) => d.wasiyyaRecipients = v),
          ),
        ],
      );
}

class _HeirsStep extends StatelessWidget {
  const _HeirsStep(this.draft, this.notifier);
  final WillDraft draft;
  final WillDraftNotifier notifier;

  static const groups = <String, List<(String, String)>>{
    'Spouse': [('husband', 'Husband'), ('wife', 'Wives (up to 4)')],
    'Descendants': [
      ('son', 'Sons'), ('daughter', 'Daughters'),
      ('sons_son', "Son's sons"), ('sons_daughter', "Son's daughters"),
    ],
    'Parents & grandparents': [
      ('father', 'Father'), ('mother', 'Mother'),
      ('paternal_grandfather', 'Paternal grandfather'),
      ('paternal_grandmother', 'Paternal grandmother'),
      ('maternal_grandmother', 'Maternal grandmother'),
    ],
    'Siblings': [
      ('full_brother', 'Full brothers'), ('full_sister', 'Full sisters'),
      ('paternal_brother', 'Paternal half-brothers'),
      ('paternal_sister', 'Paternal half-sisters'),
      ('maternal_brother', 'Maternal half-brothers'),
      ('maternal_sister', 'Maternal half-sisters'),
    ],
    'Wider family': [
      ('full_brothers_son', "Full brothers' sons"),
      ('paternal_brothers_son', "Paternal brothers' sons"),
      ('full_paternal_uncle', 'Full paternal uncles'),
      ('paternal_paternal_uncle', 'Paternal (half) uncles'),
      ('full_uncles_son', "Full uncles' sons"),
      ('paternal_uncles_son', "Paternal uncles' sons"),
    ],
  };

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final e in groups.entries) ...[
            Padding(
              padding: const EdgeInsets.only(top: 12, bottom: 4),
              child: Text(e.key,
                  style: Theme.of(context).textTheme.titleSmall),
            ),
            for (final (rel, label) in e.value)
              Row(children: [
                Expanded(child: Text(label)),
                IconButton(
                  icon: const Icon(Icons.remove_circle_outline),
                  onPressed: () => notifier.update((d) =>
                      d.setHeirCount(rel, d.heirCount(rel) - 1)),
                ),
                Text('${draft.heirCount(rel)}'),
                IconButton(
                  icon: const Icon(Icons.add_circle_outline),
                  onPressed: () {
                    final max = switch (rel) {
                      'husband' || 'father' || 'mother' ||
                      'paternal_grandfather' || 'paternal_grandmother' ||
                      'maternal_grandmother' => 1,
                      'wife' => 4,
                      _ => 20,
                    };
                    notifier.update((d) => d.setHeirCount(
                        rel, (d.heirCount(rel) + 1).clamp(0, max)));
                  },
                ),
              ]),
          ],
          const SizedBox(height: 8),
          const Text(
            'Non-Muslim relatives and adopted children do not inherit by '
            'faraid — provide for them through the wasiyya. Mark '
            'individual heirs\' details on the next screens of the full '
            'flow.',
            style: TextStyle(fontSize: 12),
          ),
        ],
      );
}

class _ExecutorStep extends StatelessWidget {
  const _ExecutorStep(this.draft, this.notifier);
  final WillDraft draft;
  final WillDraftNotifier notifier;

  Widget _person(String label, Person p) => TextFormField(
        initialValue: p.name,
        decoration: InputDecoration(labelText: label),
        onChanged: (v) => notifier.update((_) => p.name = v),
      );

  @override
  Widget build(BuildContext context) {
    final conflicts = draft.witnessConflicts();
    return Column(children: [
      _person('Executor name', draft.executor),
      _person('Backup executor name', draft.backupExecutor),
      TextFormField(
        initialValue: draft.guardian,
        decoration: const InputDecoration(
            labelText: 'Guardian for minor children (if any)'),
        onChanged: (v) => notifier.update((d) => d.guardian = v),
      ),
      const SizedBox(height: 12),
      _person('Witness 1 name', draft.witness1),
      _person('Witness 2 name', draft.witness2),
      if (conflicts.isNotEmpty)
        Card(
          color: Colors.red.shade50,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Text(
              'Wills Act 1837 s.15: ${conflicts.join(", ")} appears to be '
              'a beneficiary — a gift to a witness (or their spouse) '
              'fails. Choose different witnesses.',
              style: const TextStyle(fontSize: 12),
            ),
          ),
        )
      else
        const Card(
          child: Padding(
            padding: EdgeInsets.all(12),
            child: Text(
              'Witnesses must be 18+, of sound mind, and must NOT be '
              'beneficiaries or spouses of beneficiaries (Wills Act 1837 '
              's.15). Both must be present together when you sign.',
              style: TextStyle(fontSize: 12),
            ),
          ),
        ),
      TextFormField(
        initialValue: draft.funeralWishes,
        maxLines: 2,
        decoration: const InputDecoration(labelText: 'Funeral wishes'),
        onChanged: (v) => notifier.update((d) => d.funeralWishes = v),
      ),
    ]);
  }
}

class _ReviewStep extends StatelessWidget {
  const _ReviewStep(this.draft);
  final WillDraft draft;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Review', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text('Name: ${draft.fullLegalName}\n'
              'Madhhab: ${draft.madhhab.label}\n'
              'Gross estate: £${draft.grossEstate.toStringAsFixed(0)}\n'
              'Wasiyya: ${draft.wasiyyaPercent.toStringAsFixed(2)}%\n'
              'Heirs: ${draft.heirs.values.map((h) =>
                  "${h.count}× ${prettyRel(h.relationship)}").join(", ")}'),
          const SizedBox(height: 8),
          const Text(
            'Press "Calculate shares" to run the faraid engine. '
            'Finalizing locks the calculation and generates the PDF '
            '(a new version is created if you edit later).',
            style: TextStyle(fontSize: 12),
          ),
        ],
      );
}
