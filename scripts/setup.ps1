# One-time setup for a teammate's laptop. Run from repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1            (backend + models)
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -NoModels  (frontend-only people)
param([switch]$NoModels, [switch]$Gpu)
$ErrorActionPreference = "Stop"
uv venv --python 3.12 .venv
if ($Gpu) { uv pip install --python .venv torch torchvision --index-url https://download.pytorch.org/whl/cu128 }
else      { uv pip install --python .venv torch torchvision --index-url https://download.pytorch.org/whl/cpu }
uv pip install --python .venv -r requirements.txt remotezip pyarrow
if (-not $NoModels) { .venv\Scripts\python scripts\download_models.py }
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Fill in .env with your API key" }
.venv\Scripts\python -c "import torch,cv2,mediapipe,transformers,fastapi; print('OK torch', torch.__version__, 'cuda', torch.cuda.is_available())"
if (Test-Path frontend\package.json) { Push-Location frontend; npm install; Pop-Location }
Write-Host "SETUP COMPLETE"
