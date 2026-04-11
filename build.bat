@echo off

rem 设置编码为UTF-8
chcp 65001

rem 清理构建缓存（保留自定义spec文件）
echo 清理构建缓存...
if exist dist rd /s /q dist
if exist build rd /s /q build
if exist __pycache__ rd /s /q __pycache__

echo 安装依赖...
pip install requests pyinstaller

rem 检查是否存在自定义spec文件
if exist siren-music-downloader.spec (
    echo 使用自定义配置文件: siren-music-downloader.spec
    python -m PyInstaller siren-music-downloader.spec --noconfirm
) else (
    echo 生成新的配置文件并构建...
    python -m PyInstaller --onefile --windowed --name siren-music-downloader main.py
)

echo.
echo 构建完成！
echo 可执行文件位于 dist\siren-music-downloader.exe

pause
