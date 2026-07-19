import 'package:cloud_functions/cloud_functions.dart';

import '../models/models.dart';

abstract class FaraidService {
  Future<CalcResult> calculate(WillDraft draft);
}

/// Production implementation: calls the `calculate_faraid` Python Cloud
/// Function (the engine of record - exact fractions, 689 unit tests).
class CloudFaraidService implements FaraidService {
  CloudFaraidService([FirebaseFunctions? functions])
      : _functions = functions ?? FirebaseFunctions.instance;
  final FirebaseFunctions _functions;

  @override
  Future<CalcResult> calculate(WillDraft draft) async {
    final callable = _functions.httpsCallable('calculate_faraid');
    final resp = await callable.call<Map<String, dynamic>>({
      'madhhab': draft.madhhab.name,
      'heirs': draft.heirs.values.map((h) => h.toJson()).toList(),
      'estate': {
        'grossEstate': draft.grossEstate,
        'funeralCosts': draft.funeralCosts,
        'debts': draft.debts,
        'unpaidMahr': draft.unpaidMahr,
        'unpaidZakat': draft.unpaidZakat,
        'kaffarat': draft.kaffarat,
        'fidya': draft.fidya,
        'wasiyyaFraction': draft.wasiyyaPercent / 100.0,
      },
    });
    return CalcResult.fromJson(Map<String, dynamic>.from(resp.data));
  }
}

/// Demo implementation used when Firebase is not configured (first run):
/// returns a representative sample so the UI is fully navigable, with a
/// clear warning that live calculation needs the backend.
class DemoFaraidService implements FaraidService {
  @override
  Future<CalcResult> calculate(WillDraft draft) async {
    return CalcResult(
      madhhab: draft.madhhab.name,
      engineVersion: 'demo',
      awlApplied: false,
      raddApplied: false,
      notes: const [],
      warnings: const [
        'DEMO MODE: connect Firebase (see README) for live faraid '
            'calculation by the verified engine. The shares below are a '
            'sample (wife + son + daughter, Hanafi).'
      ],
      blocked: const [],
      distributableGbp: draft.grossEstate,
      rows: const [
        ShareRow(relationship: 'wife', count: 1, fraction: '1/8',
            percentage: 12.5,
            reason: 'Wife: 1/8 with descendants - Qur\'an 4:12.'),
        ShareRow(relationship: 'son', count: 1, fraction: '7/12',
            percentage: 58.33,
            reason: 'Residue to sons and daughters (male share, 2:1).'),
        ShareRow(relationship: 'daughter', count: 1, fraction: '7/24',
            percentage: 29.17,
            reason: 'Residue to sons and daughters (female share, 2:1).'),
      ],
    );
  }
}
