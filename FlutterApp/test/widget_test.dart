import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:guardiantour/app.dart';
import 'package:guardiantour/providers/auth_provider.dart';
import 'package:guardiantour/providers/dashboard_provider.dart';
import 'package:guardiantour/services/api_client.dart';
import 'package:guardiantour/services/auth_service.dart';
import 'package:guardiantour/services/safety_service.dart';
import 'package:guardiantour/services/storage_service.dart';

void main() {
  testWidgets('GuardianTourApp shows splash screen on launch', (WidgetTester tester) async {
    final storage = StorageService();
    final api = ApiClient(storage);
    final authService = AuthService(api, storage);
    final safetyService = SafetyService(api);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => AuthProvider(authService, storage)),
          ChangeNotifierProvider(create: (_) => DashboardProvider(safetyService, storage)),
        ],
        child: const GuardianTourApp(),
      ),
    );

    expect(find.text('GuardianTour'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
