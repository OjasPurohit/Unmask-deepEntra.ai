# Teammate setup (Windows, ~15 min + model download)

## 1. Install tools — paste in PowerShell (Admin not required)
```powershell
winget install -e --accept-source-agreements --accept-package-agreements --id Git.Git; winget install -e --accept-package-agreements --id GitHub.cli; winget install -e --accept-package-agreements --id OpenJS.NodeJS.LTS; winget install -e --accept-package-agreements --id astral-sh.uv; winget install -e --accept-package-agreements --id Google.AntigravityIDE
```
Close and reopen PowerShell after it finishes (so PATH updates).

## 2. Connect GitHub + clone
```powershell
gh auth login --web --git-protocol https; gh auth setup-git; git config --global user.name "YOUR NAME"; git config --global user.email "YOUR_GITHUB_EMAIL"
gh repo clone OWNER/veritas-lens C:\Work\veritas-lens; cd C:\Work\veritas-lens
```
Open that folder in Antigravity (File → Open Folder). Its Source Control panel uses the same git login.

## 3. Python env + models
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1          # backend people (A, B, D) — downloads ~5 GB models
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Gpu     # same, if you have an NVIDIA GPU
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -NoModels  # frontend person (C)
```
Faster: copy `models\` and `data\` folders from Ojas's pen drive instead of downloading.

## 4. Git workflow tomorrow
Own branch per person (`core`, `signals`, `ui`, `eval`). Merge into `main` at 1:45, 2:45, 3:15. Pull `main` right after each merge.

## 5. Your Antigravity context file
- Training / evaluation owner → `context/TRAINING_CONTEXT.md`
- Frontend / UI owner → `context/FRONTEND_CONTEXT.md`
- Everyone → `CLAUDE.md` + `PLAN.md` (AGENTS.md points agents to them automatically)
