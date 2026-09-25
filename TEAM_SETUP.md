# Teammate setup (Windows, ~15 min + model download)

## 1. Install tools — paste in PowerShell (Admin not required)
```powershell
winget install -e --accept-source-agreements --accept-package-agreements --id Git.Git; winget install -e --accept-package-agreements --id GitHub.cli; winget install -e --accept-package-agreements --id OpenJS.NodeJS.LTS; winget install -e --accept-package-agreements --id astral-sh.uv; winget install -e --accept-package-agreements --id Google.AntigravityIDE
```
Close and reopen PowerShell after it finishes (so PATH updates).

## 2. Connect GitHub + clone
```powershell
gh auth login --web --git-protocol https; gh auth setup-git; git config --global user.name "YOUR NAME"; git config --global user.email "YOUR_GITHUB_EMAIL"
gh repo clone OjasPurohit/DeepEntra-Build-Fest-Masons-CYB-03 C:\Work\veritas-lens; cd C:\Work\veritas-lens
```
Open that folder in Antigravity (File → Open Folder). Its Source Control panel uses the same git login.

## 3. Python env + models
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1          # Omkar, Yadnesh, Ojas — downloads ~5 GB models
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Gpu     # same, if you have an NVIDIA GPU
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -NoModels  # Palash (frontend only)
```
Faster: copy `models\` and `data\` folders from Ojas's pen drive instead of downloading.

## 4. Android toolchain (Ojas + Palash, do BEFORE the event)
The Android app is Capacitor wrapping the same React build (`context/ANDROID_APP.md`). The toolchain is a ~6 GB download and a slow first Gradle run — doing it at the venue would cost us the demo.
```powershell
winget install -e --id Microsoft.OpenJDK.21
winget install -e --id Google.AndroidStudio
```
1. **Open Android Studio once** and let the setup wizard install the Android SDK, SDK Platform-Tools and a build-tools version. Nothing else is needed from the IDE.
2. **Set the environment variables** (user-level; reopen PowerShell afterwards):
   ```powershell
   setx ANDROID_HOME "$env:LOCALAPPDATA\Android\Sdk"
   setx JAVA_HOME "C:\Program Files\Microsoft\jdk-21.0.5.11-hotspot"   # check the real folder name under C:\Program Files\Microsoft
   setx PATH "$env:PATH;$env:LOCALAPPDATA\Android\Sdk\platform-tools"
   ```
   Verify: `java -version` prints 21, and `adb version` works.
3. **Enable USB debugging on a phone:** Settings → About phone → tap "Build number" 7 times → Developer options → USB debugging on. Plug it in, accept the RSA prompt, and check `adb devices` lists it.
4. **Verify the whole toolchain OUTSIDE this repo** — this is a toolchain test, not product code, so it must not live in the project:
   ```powershell
   cd C:\Work; npm create vite@latest captest -- --template react-ts; cd captest; npm i
   npm i @capacitor/core @capacitor/cli @capacitor/android
   npx cap init captest com.example.captest --web-dir dist
   npm run build; npx cap add android; npx cap sync android
   cd android; .\gradlew assembleDebug
   adb install -r app\build\outputs\apk\debug\app-debug.apk
   ```
   If a blank app opens on the phone, the toolchain is proven. Delete `C:\Work\captest` afterwards.

Common first-run problems, all better solved today than at 2:45 PM: Gradle cannot find a JDK (`JAVA_HOME` wrong), "SDK location not found" (`ANDROID_HOME` wrong), or the first `gradlew` run taking 10+ minutes while it downloads Gradle.

## 5. Git workflow tomorrow
Own branch per person: `main` (Ojas, scaffold + merges) · `ui` (Palash) · `models` (Omkar) · `backend` (Yadnesh) · `app` (Ojas, Android).
Merge into `main` at 1:45, 2:45 and 3:15. Pull `main` right after each merge. Never edit a file someone else owns — the file → owner table is in `PLAN.md` §3.1.

## 6. Your Antigravity context file
| You | Read |
|---|---|
| **Ojas** — lead / frontend / Android | `context/FRONTEND_OJAS_PALASH.md` + `context/ANDROID_APP.md` |
| **Palash** — frontend / Android UI | `context/FRONTEND_OJAS_PALASH.md` + `context/ANDROID_APP.md` |
| **Omkar** — AI models | `context/OMKAR_AI_MODELS.md` |
| **Yadnesh** — backend / ML | `context/YADNESH_BACKEND.md` |
| Everyone | `CLAUDE.md` + `PLAN.md` (AGENTS.md points agents to them automatically), and your prompt in `KICKOFF_PROMPTS.md` |
