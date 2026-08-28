# GuardianTour — Flutter App

Real Flutter/Dart app wired to your `TouristAI/backend` FastAPI service.
Styling ported 1:1 from `Flutter_app_prototype_not_working/style.css`
(same colors, card radii, SOS button, risk pill, bottom-nav tabs).

**This did not exist before** — the zip's `flutter_app/` folder was empty
and the "prototype" was an HTML/CSS/JS mockup with random-number
simulation, not Dart. Every screen here calls the real backend endpoints;
none of the values are faked.

## 1. Generate platform folders (one-time)

I could not run the Flutter SDK in the sandbox that built this (no
internet access to pub.dev), so `android/` and `ios/` folders aren't
included. Generate them without touching any of the code above:

```bash
cd guardiantour
flutter create . --org com.guardiantour --project-name guardiantour
```

This only adds the missing platform folders — it will not overwrite
`lib/`, `pubspec.yaml`, or anything else already in this zip.

## 2. Add permissions (required for GPS + SOS)

**`android/app/src/main/AndroidManifest.xml`** — inside `<manifest>`, above `<application>`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
```

**`ios/Runner/Info.plist`** — inside the top-level `<dict>`:

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>GuardianTour needs your location to detect safety anomalies and route SOS alerts.</string>
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>GuardianTour needs your location to detect safety anomalies and route SOS alerts.</string>
```

## 3. Install dependencies

```bash
flutter pub get
```

## 4. Point the app at your backend

Edit the default in `lib/config/api_config.dart`, or pass it at run time
(no code change needed):

```bash
# Android emulator (backend running on your host machine):
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000

# iOS simulator:
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000

# Physical device on the same Wi-Fi (use your machine's LAN IP):
flutter run --dart-define=API_BASE_URL=http://192.168.1.23:8000
```

## 5. Start the real backend + seed a demo zone

```bash
cd ../TouristAI/backend
cp .env.example .env
# edit .env: point DATABASE_URL / DATABASE_URL_SYNC at your Postgres,
# or use sqlite+aiosqlite:///./dev.db for a quick local run
pip install -e ".[dev]"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
python scripts/seed_data.py   # creates at least one zone; the app needs ≥1 zone
```

The app will 404/empty-state gracefully if no zones exist yet, but the
risk feed needs at least one `GET /api/v1/zones/` result.

## 6. Run

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

## What's wired to what

| Screen | Real backend calls |
|---|---|
| Login / Register | `POST /auth/register`, `POST /auth/login`, `GET /users/me` |
| Splash | `GET /users/me` (session restore), token refresh via `POST /auth/refresh` |
| Safety Hub → location card | `POST /gps/location` every 20s, reads `is_anomalous`, `in_high_risk_zone`, `should_trigger_sos` |
| Safety Hub → Edge-AI card | `POST /detection/audio` — demo buttons send real SCREAM/GLASS_BREAK/NORMAL classifications; high-confidence SCREAM/GLASS_BREAK genuinely triggers SOS |
| Safety Hub → SOS card | `POST /sos/manual` with idempotency key |
| Safety Hub → risk feed | `GET /weather/location`, `GET /news/`, `POST /risk/calculate/{zone_id}` (falls back to `GET /risk/zone/{zone_id}`) |
| Mesh Net tab | `POST /mesh/nodes` (self-register once), `GET /mesh/nodes`, `GET /mesh/stats`, `GET /mesh/route/{node_id}` (A*) |
| Blockchain ID tab | `POST /blockchain/register`, `GET /blockchain/verify/{user_id}` |
| Profile sheet | Local session data + logout via `POST /auth/logout` |

GPS anomalies that flip `should_trigger_sos` to `true`, and high-confidence
audio detections, both call the real `/sos/manual` flow automatically —
this mirrors the prototype's "Edge-AI Trigger" behavior but with an actual
backend round-trip instead of `Math.random()`.

## What's still open

- No live map tile view yet (Safety Hub shows lat/lon + zone badge instead
  of a Google/Mapbox map — add `google_maps_flutter` if you want tiles).
- SMS/mesh-fallback *tiers* shown in the old mockup aren't a real backend
  concept yet — the SOS card currently reflects only the single real
  `/sos/manual` → `/communication/sos/...` pipeline your backend has.
  If you want the 3-tier Internet → SMS → Mesh UI back, that logic needs
  to exist server-side first (check `communication` and `mesh` routers).
- No push notifications for responders — out of scope for this pass.
