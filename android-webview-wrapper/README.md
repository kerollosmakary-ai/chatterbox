# Notebook Studio Android WebView Wrapper

This is a separate Android app that wraps the existing Notebook Studio web UI in a WebView shell.

- Python Studio backend remains unchanged at `/home/runner/work/chatterbox/chatterbox/studio`.
- Wrapper project lives in `/home/runner/work/chatterbox/chatterbox/android-webview-wrapper`.

## URL strategy

The wrapper has two URLs (configured via Gradle properties):

- `STUDIO_PROD_URL` (release/default target)
- `STUDIO_LOCAL_URL` (debug target for LAN testing)

By default:

- release uses `STUDIO_PROD_URL`
- debug uses `STUDIO_LOCAL_URL`

Set custom URLs in `/home/runner/work/chatterbox/chatterbox/android-webview-wrapper/gradle.properties` or via CLI:

```bash
./gradlew assembleDebug -PSTUDIO_LOCAL_URL=http://192.168.1.10:7860
./gradlew assembleRelease -PSTUDIO_PROD_URL=https://your-studio-domain.example.com
```

> For local testing on a phone, run backend on your computer and use its LAN IP. Do **not** use `localhost` from Android.

## Local backend run

From repo root:

```bash
python /home/runner/work/chatterbox/chatterbox/studio/main.py
```

Then point `STUDIO_LOCAL_URL` to `http://<your-lan-ip>:7860`.

## WebView capabilities included

- JavaScript enabled
- DOM storage enabled
- Media playback without forced gesture
- File upload chooser support
- Cookies/session support
- In-app handling for HTTP/HTTPS links

## UX safeguards included

- Loading indicator
- Pull-to-refresh
- Retry screen for network/server failures
- Android back button navigates WebView history first

## Cleartext/network policy

- `INTERNET` and `ACCESS_NETWORK_STATE` permissions are enabled.
- Debug builds allow cleartext HTTP (`usesCleartextTraffic=true`) to support local LAN testing.
- Release builds disable cleartext HTTP by default.

## Build and sign

### Debug APK

```bash
cd /home/runner/work/chatterbox/chatterbox/android-webview-wrapper
./gradlew assembleDebug
```

Output:

`app/build/outputs/apk/debug/app-debug.apk`

### Release APK/AAB

1. Create signing config in `~/.gradle/gradle.properties` (recommended):
   - `ANDROID_KEYSTORE_PATH`
   - `ANDROID_KEYSTORE_PASSWORD`
   - `ANDROID_KEY_ALIAS`
   - `ANDROID_KEY_PASSWORD`
2. Release signing is auto-wired in `app/build.gradle.kts` when these properties are present.
   If they are missing, release build falls back to debug signing.
3. Build:

```bash
./gradlew assembleRelease
./gradlew bundleRelease
```

## End-to-end validation checklist

Validate on a real Android device:

1. Launch app and confirm Studio loads.
2. Open settings and save API key/provider/model.
3. Upload source file(s) and URL source.
4. Generate Summary/Key Points/Study Guide/FAQ.
5. Generate podcast and confirm audio playback.
6. Verify back navigation and retry flow during network outage.
