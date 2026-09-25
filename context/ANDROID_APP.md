# Context: ANDROID APP — Veritas Lens (CYB-03)
> Owners: **Ojas** (Capacitor config, build, backend/LAN wiring, APK) + **Palash** (mobile-responsive UI, camera/upload flow).
> Also read ../CLAUDE.md, ../PLAN.md §3 and `FRONTEND_OJAS_PALASH.md`.

## Mission in one line
Put Veritas Lens **on a phone** — an admissions officer photographs or picks an applicant photo and gets the same evidence report — **without writing a second app**.

## Approach: Capacitor wrapping the same React build
No separate native codebase. Capacitor packages the existing `frontend/dist` into an Android webview APK.
```bash
cd frontend
npm i @capacitor/core @capacitor/cli @capacitor/android
npx cap init "Veritas Lens" ai.veritaslens.app --web-dir dist
```
`capacitor.config.ts`:
```ts
import type { CapacitorConfig } from '@capacitor/cli';
const config: CapacitorConfig = {
  appId: 'ai.veritaslens.app',
  appName: 'Veritas Lens',
  webDir: 'dist',
  server: { cleartext: true },   // backend is plain http on the LAN
};
export default config;
```
Also set `android:usesCleartextTraffic="true"` on `<application>` in `android/app/src/main/AndroidManifest.xml` — without it Android silently blocks every `http://` call to the laptop.

**The models never run on the phone.** They stay on the verification laptop; the phone is a client that POSTs the file to the FastAPI backend over LAN / phone hotspot and renders the JSON result.

## Frontend rules this depends on (Palash + Ojas, also listed in `FRONTEND_OJAS_PALASH.md`)
1. **One API base.** `const BASE = localStorage.getItem('veritas_api') ?? import.meta.env.VITE_API_BASE ?? ''`. Default `''` → the Vite proxy handles the web build. The APK build sets `VITE_API_BASE=http://<laptop-LAN-IP>:8000`.
2. **One URL helper.** Every image/static/heatmap/thumb URL goes through `apiUrl(path)` which prefixes `BASE`. Never hard-code `/static/...` into an `<img src>`.
3. **Settings field.** A Settings screen (or a gear in the nav) lets the user type the backend URL at runtime; it is saved to `localStorage` under `veritas_api`. The venue IP is unknown in advance — this is the single most important mobile feature.
4. **390 px.** Every page must be usable at 390 px width: nav collapses, the heatmap viewer and its opacity slider stack vertically, tables scroll horizontally inside their own container.
5. **Camera.** The upload input is `<input type="file" accept="image/*,video/*" capture>` so the phone opens the camera directly; keep drag-and-drop for desktop.

## Backend requirements (Ojas, in `backend/app.py`)
- `CORSMiddleware` with `allow_origins=["*"]`, all methods and headers (the webview origin is `http://localhost` / `capacitor://`, not our host).
- Run uvicorn as `.venv\Scripts\uvicorn backend.app:app --host 0.0.0.0 --port 8000`.
- Open the Windows firewall once:
  `New-NetFirewallRule -DisplayName "Veritas 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow`
- Find the LAN IP with `ipconfig` (Wi-Fi IPv4, e.g. `192.168.1.23`). Phone and laptop must be on the same Wi-Fi or the laptop on the phone's hotspot.

## Build steps
```bash
cd frontend
# .env.production:  VITE_API_BASE=http://<laptop-LAN-IP>:8000
npm run build
npx cap add android        # first time only
npx cap sync android       # after every web rebuild
cd android && .\gradlew assembleDebug
# APK: android/app/build/outputs/apk/debug/app-debug.apk
```
Install with `adb install -r android/app/build/outputs/apk/debug/app-debug.apk`, or just copy the APK to the phone and tap it (allow "install unknown apps").
Toolchain (JDK 21 + Android Studio SDK + `ANDROID_HOME` / `JAVA_HOME`) must already be installed — see `TEAM_SETUP.md`.

## Priority and timing
**P1.5** — do not start before the **1:45 checkpoint passes on web**. Target: working APK by **3:00**.
| Time | Step |
|---|---|
| after 1:45 | Palash confirms 390 px layout + capture input; Ojas adds CORS + `--host 0.0.0.0` + firewall rule |
| 2:00 | `npx cap add android`, first debug build, load the app against the laptop IP |
| 2:45 | APK rebuilt from the merged `main` build, installed on the demo phone, one real analysis run end-to-end |
| 3:00 | APK frozen and copied to a second phone as backup |

## Demo (30 seconds, inside the 4-minute script)
"A VSS admissions officer verifies an applicant photo from a phone" — open the app, tap upload, pick/photograph the applicant photo, the band banner and heatmap appear on the phone, the case shows up in the review queue on the projector.

## Fallback (mention in risks)
If the APK does not build or install in time, open the **web app in the phone's Chrome** at `http://<laptop-LAN-IP>:5173` (or `:8000` if the build is served by FastAPI). Identical UI, same 30-second beat, no Android toolchain needed. Say it out loud as "the same client, unpackaged" rather than hiding it.
