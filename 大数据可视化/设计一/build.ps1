# -*- coding: utf-8 -*-
# PyInstaller 打包脚本 (Windows PowerShell)
# 用法: .\build.ps1

# 检查 PyInstaller 是否已安装
$pyinstaller = pyinstaller --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 错误：PyInstaller 未安装" -ForegroundColor Red
    Write-Host "请先运行：pip install pyinstaller" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ PyInstaller 版本: $pyinstaller" -ForegroundColor Green

# 清理之前的构建
Write-Host "`n⚙️  清理旧的构建文件..." -ForegroundColor Cyan
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "AQI_System.spec") { Remove-Item "AQI_System.spec" -Force }

# PyInstaller 打包命令
Write-Host "`n📦 正在打包应用程序..." -ForegroundColor Cyan
$command = @(
    "pyinstaller",
    "--noconfirm",
    "--onedir",
    "--windowed",
    "--icon=assets/icon.ico",
    "--add-data", "config.yaml;.",
    "--add-data", "data;data/",
    "--add-data", "assets;assets/",
    "--hidden-import=customtkinter",
    "--hidden-import=matplotlib.backends.backend_tkagg",
    "--hidden-import=seaborn",
    "--hidden-import=seaborn.plotting_context",
    "--hidden-import=seaborn.palettes",
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    "--hidden-import=openai",
    "--hidden-import=yaml",
    "--hidden-import=pandas",
    "--hidden-import=numpy",
    "--hidden-import=sqlite3",
    "--hidden-import=sklearn",
    "--collect-all=seaborn",
    "--name", "AQI_System",
    "main.py"
)

& $($command[0]) $($command[1..($command.Length-1)])

# 检查打包是否成功
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ 打包成功！" -ForegroundColor Green
    Write-Host "`n📁 应用程序位置: .\dist\AQI_System\" -ForegroundColor Green
    Write-Host "🚀 运行方式: .\dist\AQI_System\AQI_System.exe" -ForegroundColor Green
    
    # 提示检查配置
    Write-Host "`n⚠️  重要提示：" -ForegroundColor Yellow
    Write-Host "1. 确保 config.yaml 中已填入有效的 DeepSeek API Key"
    Write-Host "2. config.yaml 必须与 AQI_System.exe 在同一目录"
    Write-Host "3. data 和 assets 文件夹会自动创建"
} else {
    Write-Host "`n❌ 打包失败，请检查错误信息" -ForegroundColor Red
    exit 1
}
