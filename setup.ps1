# setup.ps1 — создаёт всю структуру проекта Максидом Smart Calculators

$ErrorActionPreference = "Stop"

# ---------- Папки ----------
"app","app\domain","app\services","app\ml","static","data",".vscode" |
    ForEach-Object { New-Item -ItemType Directory -Path $_ -Force | Out-Null }

# ---------- Пустые __init__.py ----------
"app\__init__.py","app\domain\__init__.py","app\services\__init__.py","app\ml\__init__.py" |
    ForEach-Object { New-Item -ItemType File -Path $_ -Force | Out-Null }

Write-Host "Папки созданы" -ForegroundColor Green