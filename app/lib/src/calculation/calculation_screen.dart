import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/models.dart';
import '../state/providers.dart';

/// M3: renders the faraid result - pie chart (fl_chart), shares table
/// with per-heir explanations, blocked heirs, awl/radd flags, warnings.
class CalculationScreen extends ConsumerWidget {
  const CalculationScreen({super.key, required this.willId});
  final String willId;

  static const _palette = [
    Colors.teal, Colors.orange, Colors.indigo, Colors.pink, Colors.green,
    Colors.brown, Colors.blueGrey, Colors.purple, Colors.red, Colors.cyan,
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final calc = ref.watch(calculationProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Faraid shares')),
      body: calc.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text('Calculation failed: $e'),
          ),
        ),
        data: (r) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            for (final w in r.warnings)
              Card(
                color: Colors.amber.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(w, style: const TextStyle(fontSize: 12)),
                ),
              ),
            SizedBox(
              height: 220,
              child: PieChart(PieChartData(sections: [
                for (final (i, row) in r.rows.indexed)
                  PieChartSectionData(
                    value: row.percentage,
                    color: _palette[i % _palette.length],
                    title: '${prettyRel(row.relationship)}\n'
                        '${row.fraction}',
                    titleStyle: const TextStyle(
                        fontSize: 10, color: Colors.white),
                    radius: 90,
                  ),
              ])),
            ),
            const SizedBox(height: 12),
            Text('Engine ${r.engineVersion} · ${r.madhhab}'
                '${r.awlApplied ? " · awl applied" : ""}'
                '${r.raddApplied ? " · radd applied" : ""}'),
            const SizedBox(height: 8),
            for (final row in r.rows)
              ListTile(
                dense: true,
                title: Text('${prettyRel(row.relationship)}'
                    '${row.count > 1 ? " ×${row.count}" : ""} — '
                    '${row.fraction} '
                    '(${row.percentage.toStringAsFixed(2)}%)'),
                subtitle: Text(row.reason,
                    style: const TextStyle(fontSize: 11)),
                trailing: r.distributableGbp == null
                    ? null
                    : Text('£${(r.distributableGbp! * row.percentage / 100)
                        .toStringAsFixed(0)}'),
              ),
            if (r.blocked.isNotEmpty) ...[
              const Divider(),
              Text('Not inheriting',
                  style: Theme.of(context).textTheme.titleSmall),
              for (final b in r.blocked)
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.block, size: 18),
                  title: Text(prettyRel(b['relationship'] as String)),
                  subtitle: Text(b['reason'] as String? ?? '',
                      style: const TextStyle(fontSize: 11)),
                ),
            ],
            for (final n in r.notes)
              Card(
                color: Colors.teal.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(n, style: const TextStyle(fontSize: 12)),
                ),
              ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: () => context.go('/dashboard'),
              child: const Text('Finalize & track my will'),
            ),
          ],
        ),
      ),
    );
  }
}
