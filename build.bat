@echo off

rem 设置编码为UTF-8
chcp 65001

rem 清理文件缓存
echo 清理文件缓存...
if exist dist rd /s /q dist
if exist build rd /s /q build
if exist __pycache__ rd /s /q __pycache__
if exist siren-music-downloader.spec del /f /q siren-music-downloader.spec

echo 安装依赖...
pip install requests pyinstaller

echo 构建可执行文件...
python -m PyInstaller --onefile --windowed --name siren-music-downloader main.py

echo 构建完成！
echo 可执行文件位于 dist\siren-music-downloader.exe

pause
