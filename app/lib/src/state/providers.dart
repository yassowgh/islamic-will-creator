import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/models.dart';
import '../services/faraid_service.dart';

/// Flip to CloudFaraidService() once Firebase is configured (M1 setup).
final faraidServiceProvider =
    Provider<FaraidService>((ref) => DemoFaraidService());

class WillDraftNotifier extends Notifier<WillDraft> {
  @override
  WillDraft build() => WillDraft();

  void update(void Function(WillDraft d) fn) {
    fn(state);
    ref.notifyListeners();
    _bump();
  }

  int _version = 0;
  void _bump() => _version++;
}

final willDraftProvider =
    NotifierProvider<WillDraftNotifier, WillDraft>(WillDraftNotifier.new);

final calculationProvider = FutureProvider.autoDispose<CalcResult>((ref) {
  final draft = ref.watch(willDraftProvider);
  return ref.watch(faraidServiceProvider).calculate(draft);
});
