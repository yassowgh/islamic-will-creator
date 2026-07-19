import 'package:flutter_test/flutter_test.dart';
import 'package:islamic_will_creator/main.dart';

void main() {
  testWidgets('app builds', (tester) async {
    await tester.pumpWidget(const IwcApp());
    expect(find.byType(IwcApp), findsOneWidget);
  });
}
