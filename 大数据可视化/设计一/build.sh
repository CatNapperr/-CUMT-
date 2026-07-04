#!/bin/bash
# PyInstaller 打包脚本 (Linux/macOS)
# 用法: bash build.sh

# 检查 PyInstaller 是否已安装
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ 错误：PyInstaller 未安装"
    echo "请先运行：pip install pyinstaller"
    exit 1
fi

echo "✓ PyInstaller 已安装"

# 清理之前的构建
echo ""
echo "⚙️  清理旧的构建文件..."
rm -rf dist build AQI_System.spec

# PyInstaller 打包命令
echo ""
echo "📦 正在打包应用程序..."
pyinstaller \
    --noconfirm \
    --onedir \
    --windowed \
    --add-data "config.yaml:." \
    --add-data "data:data/" \
    --add-data "assets:assets/" \
    --hidden-import=customtkinter \
    --hidden-import=matplotlib.backends.backend_tkagg \
    --hidden-import=seaborn \
    --hidden-import=seaborn.plotting_context \
    --hidden-import=seaborn.palettes \
    --hidden-import=PIL \
    --hidden-import=PIL.Image \
    --hidden-import=openai \
    --hidden-import=yaml \
    --hidden-import=pandas \
    --hidden-import=numpy \
    --hidden-import=sqlite3 \
    --hidden-import=sklearn \
    --collect-all=seaborn \
    --name "AQI_System" \
    main.py

# 检查打包是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ 打包成功！"
    echo ""
    echo "📁 应用程序位置: ./dist/AQI_System/"
    echo "🚀 运行方式: ./dist/AQI_System/AQI_System"
    echo ""
    echo "⚠️  重要提示："
    echo "1. 确保 config.yaml 中已填入有效的 DeepSeek API Key"
    echo "2. config.yaml 必须与 AQI_System 可执行文件在同一目录"
    echo "3. data 和 assets 文件夹会自动创建"
else
    echo ""
    echo "❌ 打包失败，请检查错误信息"
    exit 1
fi
